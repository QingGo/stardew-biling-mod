"""
Python XNB packer for SpriteFont (uncompressed, Windows target).
Writes chars as 7-bit encoded integers (FNA/MonoGame format),
NOT UTF-8 (which xnbcli incorrectly uses).

XNB SpriteFont content order:
  1. Texture2D (reader idx 2)
  2. List<Rectangle> glyphs (reader idx 3)
  3. List<Rectangle> cropping (reader idx 3)
  4. List<char> characterMap (reader idx 5)
  5. int32 lineSpacing (primitive)
  6. float spacing (primitive)
  7. List<Vector3> kerning (reader idx 7)
  8. Nullable<char> defaultCharacter (byte hasValue + optional 7bit char)
"""
import json, struct, os, sys
from PIL import Image

def write_7bit(buf, val):
    """Write a 7-bit encoded integer (variable-length)."""
    while val >= 0x80:
        buf.append((val & 0x7F) | 0x80)
        val >>= 7
    buf.append(val & 0x7F)

def write_7bit_char(buf, char):
    """Write a single char as 7-bit encoded integer (Unicode code point)."""
    write_7bit(buf, ord(char))

def write_string(buf, s):
    """Write a 7-bit length-prefixed UTF-8 string."""
    encoded = s.encode('utf-8')
    write_7bit(buf, len(encoded))
    buf.extend(encoded)

def write_int32(buf, val):
    buf.extend(struct.pack('<i', val))

def write_uint32(buf, val):
    buf.extend(struct.pack('<I', val))

def write_single(buf, val):
    buf.extend(struct.pack('<f', val))

def write_byte(buf, val):
    buf.append(val & 0xFF)

def pack_spritefont(json_path, png_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    content = data['content']

    # Load PNG and convert to premultiplied BGRA
    img = Image.open(png_path).convert('RGBA')
    w, h = img.size
    pixels = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b, a = img.getpixel((x, y))
            if a > 0:
                r = (r * a) // 255
                g = (g * a) // 255
                b = (b * a) // 255
            pixels.extend([b, g, r, a])  # BGRA

    # Build body
    body = bytearray()

    # --- Type readers ---
    readers = data.get('readers', [])
    write_7bit(body, len(readers))
    for reader in readers:
        write_string(body, reader['type'])
        write_int32(body, reader.get('version', 0))

    # --- Shared resources (always 0) ---
    write_7bit(body, 0)

    # --- Content: SpriteFont (reader index 1) ---
    write_7bit(body, 1)

    # 1. Texture2D (reader index 2)
    write_7bit(body, 2)
    write_int32(body, 0)       # format = SurfaceFormat.Color (uncompressed)
    write_uint32(body, w)      # width
    write_uint32(body, h)      # height
    write_uint32(body, 1)      # mipCount
    write_uint32(body, len(pixels))  # dataSize
    body.extend(pixels)        # pixel data (premultiplied BGRA32)

    # 2. List<Rectangle> glyphs (reader index 3)
    glyphs = content.get('glyphs', [])
    write_7bit(body, 3)
    write_uint32(body, len(glyphs))
    for g in glyphs:
        write_int32(body, g['x'])
        write_int32(body, g['y'])
        write_int32(body, g['width'])
        write_int32(body, g['height'])

    # 3. List<Rectangle> cropping (reader index 3)
    cropping = content.get('cropping', [])
    write_7bit(body, 3)
    write_uint32(body, len(cropping))
    for c in cropping:
        write_int32(body, c['x'])
        write_int32(body, c['y'])
        write_int32(body, c['width'])
        write_int32(body, c['height'])

    # 4. List<char> characterMap (reader index 5)
    #    Each char written as 7-bit encoded integer (NOT UTF-8!)
    chars = content.get('characterMap', [])
    write_7bit(body, 5)
    write_uint32(body, len(chars))
    for c in chars:
        write_7bit_char(body, c)

    # 5. int32 lineSpacing (primitive, no reader index)
    line_spacing = content.get('verticalLineSpacing', content.get('lineSpacing', 0))
    write_int32(body, line_spacing)

    # 6. float spacing (primitive, no reader index)
    spacing = content.get('horizontalSpacing', content.get('spacing', 0.0))
    write_single(body, spacing)

    # 7. List<Vector3> kerning (reader index 7)
    kerning = content.get('kerning', [])
    write_7bit(body, 7)
    write_uint32(body, len(kerning))
    for k in kerning:
        write_single(body, k['x'])
        write_single(body, k['y'])
        write_single(body, k['z'])

    # 8. Nullable<char> defaultCharacter
    #    No reader index (NullableReader.writeIndex is commented out)
    default_char = content.get('defaultCharacter')
    if default_char is not None and default_char != '':
        write_byte(body, 1)
        write_7bit_char(body, default_char)
    else:
        write_byte(body, 0)

    # Verify all lists match
    assert len(glyphs) == len(cropping) == len(chars) == len(kerning), \
        f"List length mismatch: glyphs={len(glyphs)} cropping={len(cropping)} chars={len(chars)} kerning={len(kerning)}"

    # --- Build XNB file ---
    xnb = bytearray()
    xnb.extend(b'XNB')
    xnb.extend(b'w')           # platform: Windows
    write_byte(xnb, 5)         # format version
    write_byte(xnb, 0x01)      # flags: HiDef, no compression
    xnb.extend(struct.pack('<I', 0))  # placeholder file size
    xnb.extend(body)

    # Update file size at offset 6
    struct.pack_into('<I', xnb, 6, len(xnb))

    # Write output
    with open(output_path, 'wb') as f:
        f.write(xnb)

    print(f'Wrote {len(xnb)} bytes: {output_path}')
    print(f'  Texture: {w}x{h}, format=0 (Color/BGRA32)')
    print(f'  Glyphs: {len(glyphs)}, Cropping: {len(cropping)}')
    print(f'  Characters: {len(chars)}, Kerning: {len(kerning)}')
    print(f'  LineSpacing: {line_spacing}, Spacing: {spacing}')
    return True

if __name__ == '__main__':
    base_in = 'C:/Users/minam/code/stardew-bilin/_tmp/font-zh'
    base_out = 'C:/Users/minam/code/stardew-bilin/BilingualMod/assets'

    json_path = os.path.join(base_in, 'SpriteFont1.zh-CN.json')
    png_path = os.path.join(base_in, 'SpriteFont1.zh-CN.png')
    out_path = os.path.join(base_out, 'SpriteFont1.zh-CN.xnb')

    if not os.path.exists(json_path):
        print(f'Error: {json_path} not found. Run merge_font.py first.')
        sys.exit(1)

    pack_spritefont(json_path, png_path, out_path)
    print('\nDone')