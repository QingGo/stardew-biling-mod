"""
Bidirectional font merger: merge Japanese glyphs into Chinese SpriteFont
AND vice versa. Produces two merged fonts:

  - {font}.zh-CN.xnb: ZH base + JA chars not in ZH (used when game=ZH)
  - {font}.ja-JP.xnb: JA base + ZH chars not in JA (used when game=JA)

This ensures each base font keeps its own glyph style for shared CJK
ideographs (日, 本, etc.), with only the missing chars taken from the
other font.

Usage:
    python merge_font.py SpriteFont1   # merge one font both ways
    python merge_font.py SmallFont
    python merge_font.py                # merge both SpriteFont1 and SmallFont
"""
import json
import os
import shutil
import sys
from PIL import Image

TMP_BASE = 'C:/Users/minam/code/stardew-bilin/_tmp'

# Unicode ranges
HIRAGANA = set(chr(cp) for cp in range(0x3040, 0x309F + 1))
KATAKANA = set(chr(cp) for cp in range(0x30A0, 0x30FF + 1))
ALL_KANA = HIRAGANA | KATAKANA


def _merge_into(base_json, base_png, base_chars, donor_json, donor_png, donor_chars,
                out_json_path, out_png_path, base_label, donor_label):
    """Generic merger: copy donor chars missing from base into base texture.

    Writes a new JSON + PNG containing base glyphs + missing donor glyphs.
    Does NOT touch shared glyphs (base retains its own style).
    Returns the new total char count, or 0 if nothing to merge.
    """
    bc = base_json['content']
    dc = donor_json['content']

    base_set = set(base_chars)
    donor_set = set(donor_chars)
    missing = sorted(donor_set - base_set, key=ord)

    missing_kana = [c for c in missing if c in ALL_KANA]
    missing_kanji = [c for c in missing if c not in ALL_KANA and ord(c) > 0x2E00]
    missing_other = [c for c in missing if c not in ALL_KANA and ord(c) <= 0x2E00]

    print(f'    Missing chars to add from {donor_label}: {len(missing)}')
    print(f'      Kana: {len(missing_kana)}')
    print(f'      Kanji (CJK range): {len(missing_kanji)}')
    print(f'      Other: {len(missing_other)}')

    if not missing:
        print(f'    Nothing to merge; skipping {base_label}')
        return 0

    # Map donor chars to glyph data
    donor_glyph_map = dict(zip(donor_chars, dc['glyphs']))
    donor_crop_map = dict(zip(donor_chars, dc['cropping']))
    donor_kern_map = dict(zip(donor_chars, dc['kerning']))

    # Load base texture (mutable copy)
    base_img = Image.open(base_png).convert('RGBA')
    donor_img = Image.open(donor_png).convert('RGBA')

    tex_w = base_img.width
    tex_h = base_img.height
    curr_bottom = max(g['y'] + g['height'] for g in bc['glyphs'])

    MAX_ROW_W = tex_w - 10
    SIDE_MARGIN = 5
    BOTTOM_MARGIN = 5
    GLYPH_GAP = 2

    new_glyphs = []
    row_x = SIDE_MARGIN
    row_y = curr_bottom + BOTTOM_MARGIN
    row_h = 0

    for c in missing:
        g = donor_glyph_map[c]
        cr = donor_crop_map[c]
        gw, gh = g['width'], g['height']

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
    print(f'      New texture size: {tex_w}x{max(tex_h, new_bottom)}')

    # Build merged texture
    merged_h = max(tex_h, new_bottom)
    merged_img = Image.new('RGBA', (tex_w, merged_h), (0, 0, 0, 0))
    merged_img.paste(base_img, (0, 0))

    for ng in new_glyphs:
        sx, sy, sw, sh = ng['src']
        dx, dy, dw, dh = ng['dst']
        glyph = donor_img.crop((sx, sy, sx + sw, sy + sh))
        merged_img.paste(glyph, (dx, dy, dx + dw, dy + dh), glyph)

    merged_img.save(out_png_path)
    print(f'      Saved merged texture: {merged_img.size}')

    # Build merged character data
    new_characters = list(base_chars)
    new_glyphs_data = list(bc['glyphs'])
    new_cropping = list(bc['cropping'])
    new_kerning = list(bc['kerning'])

    for ng in new_glyphs:
        new_characters.append(ng['char'])
        new_glyphs_data.append({
            'x': ng['dst'][0], 'y': ng['dst'][1],
            'width': ng['glyph']['width'], 'height': ng['glyph']['height']
        })
        new_cropping.append(ng['crop'])
        new_kerning.append(donor_kern_map[ng['char']])

    # SpriteFont requires ascending order by char code point
    combined = list(zip(new_characters, new_glyphs_data, new_cropping, new_kerning))
    combined.sort(key=lambda t: ord(t[0]))
    new_characters, new_glyphs_data, new_cropping, new_kerning = map(list, zip(*combined))

    bc['characterMap'] = new_characters
    bc['glyphs'] = new_glyphs_data
    bc['cropping'] = new_cropping
    bc['kerning'] = new_kerning
    bc['texture']['export'] = os.path.basename(out_png_path)

    json.dump(base_json, open(out_json_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f'      Saved merged JSON: {len(new_characters)} characters')
    return len(new_characters)


def merge_font(font_name: str) -> None:
    """Merge JA -> ZH and ZH -> JA for a given SpriteFont."""
    zh_dir = f'{TMP_BASE}/font-zh'
    ja_dir = f'{TMP_BASE}/font-ja'
    out_zh_dir = f'{TMP_BASE}/font-merged-zh'
    out_ja_dir = f'{TMP_BASE}/font-merged-ja'

    zh_json_path = f'{zh_dir}/{font_name}.zh-CN.json'
    ja_json_path = f'{ja_dir}/{font_name}.ja-JP.json'
    zh_png_path = f'{zh_dir}/{font_name}.zh-CN.png'
    ja_png_path = f'{ja_dir}/{font_name}.ja-JP.png'

    for p, label in [(zh_json_path, 'Chinese JSON'), (ja_json_path, 'Japanese JSON'),
                     (zh_png_path, 'Chinese PNG'), (ja_png_path, 'Japanese PNG')]:
        if not os.path.exists(p):
            print(f'Error: {label} not found: {p}')
            print(f'  Run: node xnbcli.js unpack <game>/{font_name}.zh-CN.xnb {zh_dir}')
            print(f'  Run: node xnbcli.js unpack <game>/{font_name}.ja-JP.xnb {ja_dir}')
            return

    os.makedirs(out_zh_dir, exist_ok=True)
    os.makedirs(out_ja_dir, exist_ok=True)

    print(f'=== Merging {font_name} (bidirectional) ===')

    # Direction 1: ZH base + JA missing chars -> {font}.zh-CN
    print(f'  -- ZH base + JA missing --')
    # Work on copies so we don't clobber originals
    zh_json_copy = json.load(open(zh_json_path, encoding='utf-8'))
    _merge_into(
        base_json=zh_json_copy,
        base_png=zh_png_path,
        base_chars=list(zh_json_copy['content']['characterMap']),
        donor_json=json.load(open(ja_json_path, encoding='utf-8')),
        donor_png=ja_png_path,
        donor_chars=json.load(open(ja_json_path, encoding='utf-8'))['content']['characterMap'],
        out_json_path=f'{out_zh_dir}/{font_name}.zh-CN.json',
        out_png_path=f'{out_zh_dir}/{font_name}.zh-CN.png',
        base_label='ZH', donor_label='JA',
    )

    # Direction 2: JA base + ZH missing chars -> {font}.ja-JP
    print(f'  -- JA base + ZH missing --')
    ja_json_copy = json.load(open(ja_json_path, encoding='utf-8'))
    _merge_into(
        base_json=ja_json_copy,
        base_png=ja_png_path,
        base_chars=list(ja_json_copy['content']['characterMap']),
        donor_json=json.load(open(zh_json_path, encoding='utf-8')),
        donor_png=zh_png_path,
        donor_chars=json.load(open(zh_json_path, encoding='utf-8'))['content']['characterMap'],
        out_json_path=f'{out_ja_dir}/{font_name}.ja-JP.json',
        out_png_path=f'{out_ja_dir}/{font_name}.ja-JP.png',
        base_label='JA', donor_label='ZH',
    )

    print(f'  Done. Merged fonts saved in:')
    print(f'    {out_zh_dir}/{font_name}.zh-CN.json')
    print(f'    {out_ja_dir}/{font_name}.ja-JP.json')


if __name__ == '__main__':
    fonts = sys.argv[1:] if len(sys.argv) > 1 else ['SpriteFont1', 'SmallFont']
    for font_name in fonts:
        merge_font(font_name)
    print('\nDone! Now pack with: python pack_xnb.py')