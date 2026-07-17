import json
from PIL import Image

zh = json.load(open('C:/Users/minam/code/stardew-bilin/_tmp/font-zh/SpriteFont1.zh-CN.json', encoding='utf-8'))
ja = json.load(open('C:/Users/minam/code/stardew-bilin/_tmp/font-ja/SpriteFont1.ja-JP.json', encoding='utf-8'))

zc = zh['content']
jc = ja['content']

zh_chars = zc['characterMap']
ja_chars = jc['characterMap']
zh_glyphs = zc['glyphs']

# Convert to sets
zh_set = set(zh_chars)
ja_set = set(ja_chars)

# Kana ranges
hiragana = set(chr(cp) for cp in range(0x3040, 0x309F+1))
katakana = set(chr(cp) for cp in range(0x30A0, 0x30FF+1))
all_kana = hiragana | katakana

ja_kana = ja_set & all_kana
zh_kana = zh_set & all_kana
missing = sorted(ja_kana - zh_kana, key=ord)

print(f'Chinese font: {len(zh_chars)} chars, texture {zc["texture"]["format"]}')
print(f'Japanese font: {len(ja_chars)} chars, texture {jc["texture"]["format"]}')
print(f'Kana in JA: {len(ja_kana)}, in ZH: {len(zh_kana)}, missing: {len(missing)}')

if not missing:
    print('No missing kana! Chinese font has complete kana coverage.')
    # Check: maybe the Chinese font already has all kana?
    zh_hira = zh_set & hiragana
    zh_kata = zh_set & katakana
    print(f'Hiragana in ZH: {len(zh_hira)}/{len(hiragana)}')
    print(f'Katakana in ZH: {len(zh_kata)}/{len(katakana)}')
    
    # Check which specific chars are missing
    missing_hira = sorted(hiragana - zh_set)
    missing_kata = sorted(katakana - zh_set)
    print(f'Hiragana NOT in ZH: {len(missing_hira)}')
    if missing_hira:
        print('  Sample:', ' '.join(f'U+{ord(c):04X}' for c in missing_hira[:10]))
    print(f'Katakana NOT in ZH: {len(missing_kata)}')
    if missing_kata:
        print('  Sample:', ' '.join(f'U+{ord(c):04X}' for c in missing_kata[:10]))
    
    exit()

# Find glyph data for missing kana
ja_char_to_glyph = dict(zip(ja_chars, jc['glyphs']))
ja_char_to_crop = dict(zip(ja_chars, jc['cropping']))

missing_glyphs = []
for c in missing:
    g = ja_char_to_glyph.get(c)
    cr = ja_char_to_crop.get(c)
    if g:
        missing_glyphs.append({'char': c, 'code': ord(c), 'glyph': g, 'crop': cr})

# Calc space needed
max_h = max(g['glyph']['height'] for g in missing_glyphs)
total_w = sum(g['glyph']['width'] for g in missing_glyphs)
print(f'\nMissing glyphs: {len(missing_glyphs)}, max_h={max_h}, total_w={total_w}')

# Find current max bottom in ZH texture
curr_bottom = max(g['y'] + g['height'] for g in zh_glyphs) if zh_glyphs else 0
tex_h = 2048  # typical font texture size - will verify from PNG
print(f'Current texture bottom: ~{curr_bottom}px')

# Open the PNG to verify dimensions
zh_png = Image.open('C:/Users/minam/code/stardew-bilin/_tmp/font-zh/SpriteFont1.zh-CN.png')
ja_png = Image.open('C:/Users/minam/code/stardew-bilin/_tmp/font-ja/SpriteFont1.ja-JP.png')
print(f'ZH texture PNG: {zh_png.size}')
print(f'JA texture PNG: {ja_png.size}')

# Layout: arrange missing glyphs in a row at the bottom
new_y = curr_bottom + 5  # 5px padding
new_x = 5
new_glyphs = []
for g in missing_glyphs:
    w = g['glyph']['width']
    h = g['glyph']['height']
    new_glyphs.append({
        'char': g['char'],
        'code': g['code'],
        'src': (g['glyph']['x'], g['glyph']['y'], w, h),
        'dst': (new_x, new_y, w, h)
    })
    new_x += w + 2  # 2px padding

new_bottom = new_y + max_h + 5
print(f'Layout: {new_glyphs[-1]["dst"] if new_glyphs else "N/A"}')
print(f'Needed texture height: {new_bottom}')
print(f'Available: {zh_png.size[1]}')
print(f'Need resize: {new_bottom > zh_png.size[1]}')
