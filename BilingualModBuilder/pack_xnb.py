"""
Python XNB packer for SpriteFont (uncompressed, Windows target).
Chars are stored as UTF-8 bytes (matching the original game format).
Verified by inspecting raw bytes of original SpriteFont1.zh-CN.xnb:
  byte[97] = 0xC2 0xA0 = UTF-8 encoding of U+00A0

XNB SpriteFont content order:
  1. Texture2D (reader idx 2)
  2. List<Rectangle> glyphs (reader idx 3)
  3. List<Rectangle> cropping (reader idx 3)
  4. List<char> characterMap (reader idx 5)
  5. int32 lineSpacing (primitive)
  6. float spacing (primitive)
  7. List<Vector3> kerning (reader idx 7)
  8. Nullable<char> defaultCharacter (byte hasValue + optional UTF-8 char)
"""
import json, struct, os, sys
from PIL import Image

def write_7bit(buf, val):
    """Write a 7-bit encoded integer (variable-length)."""
    while val >= 0x80:
        buf.append((val & 0x7F) | 0x80)
        val >>= 7
    buf.append(val & 0x7F)

def write_utf8_char(buf, char):
    """Write a single char as UTF-8 bytes (matching original XNB format)."""
    encoded = char.encode('utf-8')
    buf.extend(encoded)

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
        write_utf8_char(body, c)

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
        write_utf8_char(body, default_char)
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
    # merge_font.py produces bidirectional outputs:
    #   _tmp/font-merged-zh/{font}.zh-CN.{json,png}  (ZH base + JA missing)
    #   _tmp/font-merged-ja/{font}.ja-JP.{json,png}  (JA base + ZH missing)
    base_zh_in = 'C:/Users/minam/code/stardew-bilin/_tmp/font-merged-zh'
    base_ja_in = 'C:/Users/minam/code/stardew-bilin/_tmp/font-merged-ja'
    base_out = 'C:/Users/minam/code/stardew-bilin/BilingualMod/assets'

    fonts = sys.argv[1:] if len(sys.argv) > 1 else ['SpriteFont1', 'SmallFont']

    for font_name in fonts:
        # Pack ZH-direction (used when game language is zh-CN)
        zh_json = os.path.join(base_zh_in, f'{font_name}.zh-CN.json')
        zh_png = os.path.join(base_zh_in, f'{font_name}.zh-CN.png')
        zh_out = os.path.join(base_out, f'{font_name}.zh-CN.xnb')
        if os.path.exists(zh_json):
            pack_spritefont(zh_json, zh_png, zh_out)
        else:
            print(f'Skip ZH pack: {zh_json} not found')

        # Pack JA-direction (used when game language is ja-JP)
        ja_json = os.path.join(base_ja_in, f'{font_name}.ja-JP.json')
        ja_png = os.path.join(base_ja_in, f'{font_name}.ja-JP.png')
        ja_out = os.path.join(base_out, f'{font_name}.ja-JP.xnb')
        if os.path.exists(ja_json):
            pack_spritefont(ja_json, ja_png, ja_out)
        else:
            print(f'Skip JA pack: {ja_json} not found')
    print('\nDone')