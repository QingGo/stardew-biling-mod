"""
Merge Japanese kana glyphs into Chinese SpriteFont.
"""
import json
from PIL import Image

# Load font data
zh = json.load(open('C:/Users/minam/code/stardew-bilin/_tmp/font-zh/SpriteFont1.zh-CN.json', encoding='utf-8'))
ja = json.load(open('C:/Users/minam/code/stardew-bilin/_tmp/font-ja/SpriteFont1.ja-JP.json', encoding='utf-8'))

zc = zh['content']
jc = ja['content']

# Load textures
zh_img = Image.open('C:/Users/minam/code/stardew-bilin/_tmp/font-zh/SpriteFont1.zh-CN.png').convert('RGBA')
ja_img = Image.open('C:/Users/minam/code/stardew-bilin/_tmp/font-ja/SpriteFont1.ja-JP.png').convert('RGBA')

# Find missing kana
zh_chars = zc['characterMap']
ja_chars = jc['characterMap']
zh_set = set(zh_chars)
ja_set = set(ja_chars)

hiragana = set(chr(cp) for cp in range(0x3040, 0x309F+1))
katakana = set(chr(cp) for cp in range(0x30A0, 0x30FF+1))
all_kana = hiragana | katakana

missing = sorted(ja_set & all_kana - zh_set, key=ord)
print(f'Missing kana: {len(missing)}')

# Map Japanese chars to glyph data
ja_glyph_map = dict(zip(ja_chars, jc['glyphs']))
ja_crop_map = dict(zip(ja_chars, jc['cropping']))
ja_kern_map = dict(zip(ja_chars, jc['kerning']))

# Calculate layout for new glyphs in Chinese texture
tex_w = zh_img.width
tex_h = zh_img.height

# Current bottom of used area
curr_bottom = max(g['y'] + g['height'] for g in zc['glyphs'])
MAX_ROW_W = tex_w - 10  # leave 5px margin on each side
SIDE_MARGIN = 5
BOTTOM_MARGIN = 5
GLYPH_GAP = 2

new_glyphs = []  # list of {char, code, src_rect, dst_rect, glyph, crop}
row_x = SIDE_MARGIN
row_y = curr_bottom + BOTTOM_MARGIN
row_h = 0

for c in missing:
    g = ja_glyph_map[c]
    cr = ja_crop_map[c]
    gw, gh = g['width'], g['height']
    
    # If glyph doesn't fit in current row, wrap to next
    if row_x + gw + SIDE_MARGIN > MAX_ROW_W and row_x > SIDE_MARGIN:
        row_y += row_h + GLYPH_GAP
        row_x = SIDE_MARGIN
        row_h = 0
    
    new_glyphs.append({
        'char': c,
        'code': ord(c),
        'src': (g['x'], g['y'], gw, gh),
        'dst': (row_x, row_y, gw, gh),
        'glyph': g,
        'crop': cr,
    })
    
    row_x += gw + GLYPH_GAP
    row_h = max(row_h, gh)

new_bottom = row_y + row_h + BOTTOM_MARGIN
print(f'New texture size: {tex_w}x{max(tex_h, new_bottom)}')

# Create enlarged texture
merged_h = max(tex_h, new_bottom)
merged_img = Image.new('RGBA', (tex_w, merged_h), (0, 0, 0, 0))
merged_img.paste(zh_img, (0, 0))

# Copy each kana glyph from Japanese texture
for ng in new_glyphs:
    sx, sy, sw, sh = ng['src']
    dx, dy, dw, dh = ng['dst']
    glyph = ja_img.crop((sx, sy, sx+sw, sy+sh))
    merged_img.paste(glyph, (dx, dy, dx+dw, dy+dh), glyph)

# Save merged texture
out_png = 'C:/Users/minam/code/stardew-bilin/_tmp/font-zh/SpriteFont1.zh-CN.png'
merged_img.save(out_png)
print(f'Saved merged texture: {merged_img.size}')

# Update character map and glyph data
new_characters = list(zh_chars)
new_glyphs_data = list(zc['glyphs'])
new_cropping = list(zc['cropping'])
new_kerning = list(zc['kerning'])

for ng in new_glyphs:
    new_characters.append(ng['char'])
    new_glyphs_data.append({
        'x': ng['dst'][0], 'y': ng['dst'][1],
        'width': ng['glyph']['width'], 'height': ng['glyph']['height']
    })
    new_cropping.append(ng['crop'])
    new_kerning.append(ja_kern_map[ng['char']])

# Update content
zc['characterMap'] = new_characters
zc['glyphs'] = new_glyphs_data
zc['cropping'] = new_cropping
zc['kerning'] = new_kerning
zc['texture']['export'] = 'SpriteFont1.zh-CN.png'

# Save updated JSON
out_json = 'C:/Users/minam/code/stardew-bilin/_tmp/font-zh/SpriteFont1.zh-CN.json'
json.dump(zh, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'Saved updated JSON: {len(new_characters)} characters')

print('\nDone! Now pack with:')
print('  xnbcli pack <json_dir> <output.xnb>')
