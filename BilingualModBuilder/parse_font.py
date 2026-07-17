"""
Parse FNA XNB SpriteFont data - uncompressed format.

FNA XNB header: "XNB" + target_platform(1) + flags(1)
If flags & 0x80: 4 bytes decompressed_size follows
Then the raw object data.

For flags=0x05: NOT compressed. Header is 9 bytes.
Data after header is raw MonoGame binary serialization.
"""
import struct, os

def read_7bit(data, pos):
    val = 0
    shift = 0
    while True:
        b = data[pos]
        val |= (b & 0x7F) << shift
        shift += 7
        pos += 1
        if (b & 0x80) == 0:
            break
    return val, pos

def parse_spritefont_xnb(path):
    data = open(path, 'rb').read()
    
    magic = data[0:3].decode('ascii')
    target = data[3]
    flags = data[4]
    assert magic == 'XNB', f"Not XNB: {magic}"
    
    compressed = bool(flags & 0x80)
    if compressed:
        decomp_size = struct.unpack('<I', data[5:9])[0]
        body_start = 13
    else:
        body_start = 9
    
    body = data[body_start:]
    pos = 0
    
    # Read type reader count
    reader_count, pos = read_7bit(body, pos)
    
    # Skip type readers
    for _ in range(reader_count):
        name_len, pos = read_7bit(body, pos)
        pos += name_len  # skip reader name
        rv = struct.unpack('<i', body[pos:pos+4])[0]
        pos += 4  # reader version
    
    # Shared resource count (always 0 for embedded fonts)
    shared_count, pos = read_7bit(body, pos)
    
    # Type reader ID for the main object
    type_id, pos = read_7bit(body, pos)
    
    print(f"  Type readers: {reader_count}")
    print(f"  Shared resources: {shared_count}")
    print(f"  Main object type ID: {type_id}")
    
    # ---- SpriteFontReader.Read() data ----
    
    # 1. Texture2D
    surface_fmt = struct.unpack('<i', body[pos:pos+4])[0]
    pos += 4
    tex_width = struct.unpack('<i', body[pos:pos+4])[0]
    pos += 4
    tex_height = struct.unpack('<i', body[pos:pos+4])[0]
    pos += 4
    mip_count = struct.unpack('<i', body[pos:pos+4])[0]
    pos += 4
    
    pixel_data_size = struct.unpack('<i', body[pos:pos+4])[0]
    pos += 4
    pixel_data = body[pos:pos + pixel_data_size]
    pos += pixel_data_size
    
    print(f"\n  Texture: {tex_width}x{tex_height}, format={surface_fmt}, mips={mip_count}")
    print(f"  Pixel data: {pixel_data_size} bytes")
    
    # Save texture as raw RGB data (for analysis)
    bpp_map = {0: 0, 1: 4, 2: 4, 3: 4, 4: 8, 5: 4, 6: 2, 7: 2, 8: 4, 9: 4, 10: 4}
    fmt_name = {0: "DXT1", 1: "Color", 2: "BGR565", 3: "BGRA4444", 
                4: "BGRA5551", 5: "BGR32", 6: "Alpha8", 7: "DXT3", 
                8: "DXT5", 9: "NormalizedByte4", 10: "Rgba1010102"}
    print(f"  Surface format: {fmt_name.get(surface_fmt, surface_fmt)}")
    
    # 2. List<Rectangle> - glyph bounds
    rect_count, pos = read_7bit(body, pos)
    glyph_bounds = []
    for _ in range(rect_count):
        x = struct.unpack('<i', body[pos:pos+4])[0]
        y = struct.unpack('<i', body[pos:pos+4])[0]
        w = struct.unpack('<i', body[pos:pos+4])[0]
        h = struct.unpack('<i', body[pos:pos+4])[0]
        pos += 16
        glyph_bounds.append((x, y, w, h))
    
    # 3. List<char> - character codes
    char_count, pos = read_7bit(body, pos)
    chars = []
    for _ in range(char_count):
        c = struct.unpack('<H', body[pos:pos+2])[0]
        pos += 2
        chars.append(chr(c))
    
    # 4. int - line spacing
    line_spacing = struct.unpack('<i', body[pos:pos+4])[0]
    pos += 4
    
    # 5. float - spacing
    spacing = struct.unpack('<f', body[pos:pos+4])[0]
    pos += 4
    
    # 6. char? - default character (optional)
    default_char = None
    if pos < len(body):
        has_default = body[pos]
        pos += 1
        if has_default:
            default_char = struct.unpack('<H', body[pos:pos+2])[0]
            pos += 2
    
    return {
        'tex_fmt': surface_fmt,
        'tex_w': tex_width,
        'tex_h': tex_height,
        'pixels': pixel_data,
        'glyph_bounds': glyph_bounds,
        'chars': chars,
        'line_spacing': line_spacing,
        'spacing': spacing,
        'default_char': default_char,
    }

# Parse both fonts
base = 'D:/steam/steamapps/common/Stardew Valley/Content/Fonts'

print("=== Chinese Font ===")
zh = parse_spritefont_xnb(f'{base}/SpriteFont1.zh-CN.xnb')
print(f"  Glyphs: {len(zh['glyph_bounds'])}")
print(f"  Characters: {len(zh['chars'])}")
print(f"  Line spacing: {zh['line_spacing']}, Spacing: {zh['spacing']}")

# Find kana in Chinese font
hiragana = set(chr(cp) for cp in range(0x3040, 0x309F+1))
katakana = set(chr(cp) for cp in range(0x30A0, 0x30FF+1))
all_kana = hiragana | katakana
zh_has_kana = [c for c in zh['chars'] if c in all_kana]
print(f"  Kana in Chinese font: {len(zh_has_kana)}/{len(all_kana)}")
if zh_has_kana:
    print(f"  Sample: {zh_has_kana[:10]}")

print("\n=== Japanese Font ===")
ja = parse_spritefont_xnb(f'{base}/SpriteFont1.ja-JP.xnb')
print(f"  Glyphs: {len(ja['glyph_bounds'])}")
print(f"  Characters: {len(ja['chars'])}")
print(f"  Line spacing: {ja['line_spacing']}, Spacing: {ja['spacing']}")

ja_has_kana = [c for c in ja['chars'] if c in all_kana]
print(f"  Kana in Japanese font: {len(ja_has_kana)}/{len(all_kana)}")

# Find kana that are in JA but not in ZH
zh_char_set = set(zh['chars'])
ja_char_set = set(ja['chars'])
missing_kana = [c for c in ja_has_kana if c not in zh_char_set]
print(f"\n  Kana in JA but not in ZH: {len(missing_kana)}")
if missing_kana:
    print(f"  U+{ord(missing_kana[0]):04X}-U+{ord(missing_kana[-1]):04X}")
    print(f"  Sample: {missing_kana[:15]}")
