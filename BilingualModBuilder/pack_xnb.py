"""
Python XNB packer for SpriteFont (uncompressed, Windows target).
Writes the merged font data directly without LZ4 compression.
"""
import json, struct, os
from PIL import Image

def write_7bit(buf, val):
    while val >= 0x80:
        buf.append((val & 0x7F) | 0x80)
        val >>= 7
    buf.append(val & 0x7F)

def write_string(buf, s):
    encoded = s.encode('utf-8')
    write_7bit(buf, len(encoded))
    buf.extend(encoded)

def write_int32(buf, val):
    buf.extend(struct.pack('<i', val))

def write_uint32(buf, val):
    buf.extend(struct.pack('<I', val))

def write_byte(buf, val):
    buf.append(val & 0xFF)

def pack_spritefont(json_path, png_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    content = data['content']
    
    # Open PNG and convert to premultiplied BGRA
    img = Image.open(png_path).convert('RGBA')
    w, h = img.size
    pixels = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b, a = img.getpixel((x, y))
            # Premultiply alpha
            if a > 0:
                r = (r * a) // 255
                g = (g * a) // 255
                b = (b * a) // 255
            pixels.extend([b, g, r, a])  # BGRA
    
    # Build body (type readers + content)
    body = bytearray()
    
    # Type reader count (7-bit)
    readers = data.get('readers', [])
    write_7bit(body, len(readers))
    
    for reader in readers:
        write_string(body, reader['type'])
        write_int32(body, reader['version'])
    
    # Shared resources (always 0)
    write_7bit(body, 0)
    
    # Content: write reader index (1-based, so 1 for first reader)
    write_7bit(body, 1)
    
    # SpriteFont data
    # Texture2D - write as uncompressed Color (format=0) to avoid DXT
    format_val = 0  # SurfaceFormat.Color = BGRA32 uncompressed
    write_int32(body, format_val)
    write_uint32(body, w)  # width
    write_uint32(body, h)  # height
    write_uint32(body, 1)  # mipCount
    write_uint32(body, len(pixels))  # dataSize
    body.extend(pixels)  # pixel data
    
    # Glyphs (List<Rectangle>)
    glyphs = content.get('glyphs', [])
    write_7bit(body, len(glyphs))
    for g in glyphs:
        write_int32(body, g['x'])
        write_int32(body, g['y'])
        write_int32(body, g['width'])
        write_int32(body, g['height'])
    
    # Characters (List<char>)
    chars = content.get('characterMap', [])
    write_7bit(body, len(chars))
    for c in chars:
        body.extend(struct.pack('<H', ord(c)))
    
    # LineSpacing (int32)
    line_spacing = content.get('verticalLineSpacing', content.get('lineSpacing', 0))
    write_int32(body, line_spacing)
    
    # Spacing (float)
    spacing = content.get('horizontalSpacing', content.get('spacing', 0.0))
    body.extend(struct.pack('<f', spacing))
    
    # DefaultCharacter (char?)
    default_char = content.get('defaultCharacter')
    if default_char is not None and default_char != '':
        write_byte(body, 1)
        body.extend(struct.pack('<H', ord(default_char)))
    else:
        write_byte(body, 0)
    
    # Build XNB file
    xnb = bytearray()
    xnb.extend(b'XNB')
    
    # Target platform
    target = data.get('header', {}).get('target', 'w')
    xnb.extend(target.encode('ascii'))
    
    # Format version
    fmt_ver = data.get('header', {}).get('formatVersion', 5)
    write_byte(xnb, fmt_ver)
    
    # Flags: HiDef (0x01) only, no compression
    hidef = data.get('header', {}).get('hidef', True)
    flags = 0x01 if hidef else 0x00
    write_byte(xnb, flags)
    
    # File size (placeholder)
    write_uint32(xnb, 0)
    
    # Append body
    body_start = len(xnb)
    xnb.extend(body)
    
    # Update file size at offset 6
    struct.pack_into('<I', xnb, 6, len(xnb))
    
    # Write output
    with open(output_path, 'wb') as f:
        f.write(xnb)
    
    print(f'Wrote {len(xnb)} bytes: {output_path}')
    print(f'  Target: {target}, Format: {fmt_ver}, HiDef: {hidef}')
    print(f'  Texture: {w}x{h}, format={format_val}')
    print(f'  Glyphs: {len(glyphs)}, Chars: {len(chars)}')
    return True

# Pack both fonts
base_in = 'C:/Users/minam/code/stardew-bilin/_tmp/font-zh'
base_out = 'C:/Users/minam/code/stardew-bilin/BilingualMod/assets'

pack_spritefont(
    f'{base_in}/SpriteFont1.zh-CN.json',
    f'{base_in}/SpriteFont1.zh-CN.png',
    f'{base_out}/SpriteFont1.zh-CN.xnb'
)

# Also do SmallFont if available
sf_json = f'{base_in.replace("font-zh", "font-pack-test")}/SmallFont.zh-CN.json'
sf_png = f'{base_in.replace("font-zh", "font-pack-test")}/SmallFont.zh-CN.png'
if os.path.exists(sf_json):
    pack_spritefont(sf_json, sf_png, f'{base_out}/SmallFont.zh-CN.xnb')
    print('SmallFont also packed')
else:
    print('SmallFont JSON not found, using original (no changes needed for SmallFont)')

print('\nDone')
