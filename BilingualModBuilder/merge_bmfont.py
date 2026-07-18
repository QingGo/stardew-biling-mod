"""
Merge two BmFont XMLs bidirectionally for ja-zh bilingual mode.

BmFont format:
  - .fnt/.xml is plain XML containing <info>, <common>, <pages>, <chars>.
  - Each <char id="X" x=".." y=".." ... page="P" /> points to texture page P.
  - Texture pages are separate XNB assets referenced by name in <page file="NAME">.

When game language = ZH, Stardew loads `Fonts/Chinese` (CHN base font + small
glyphs). Our patch Load replaces it with a merged XML containing JA chars
added to the ZN base, using Japanese texture pages as additional pages.

When game language = JA, Stardew loads `Fonts/Japanese`. Our patch replaces
it with a merged XML containing ZH chars added to the JA base, using the
Chinese texture pages as additional pages.

This preserves each base font's metrics while still having full glyph coverage.

Usage: python merge_bmfont.py
"""
import xml.etree.ElementTree as ET
import os
import shutil

ZH_DIR = 'C:/Users/minam/code/stardew-bilin/_tmp/font-zh-bmf'
JA_DIR = 'C:/Users/minam/code/stardew-bilin/_tmp/font-ja-bmf'
OUT_ZH = 'C:/Users/minam/code/stardew-bilin/_tmp/font-zh-bmf-merged'
OUT_JA = 'C:/Users/minam/code/stardew-bilin/_tmp/font-ja-bmf-merged'


def parse_font(xml_path):
    """Parse BmFont XML. Return dict with root, char_ids, page_files, info fields."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    chars_elem = root.find('chars')
    pages_elem = root.find('pages')
    common_elem = root.find('common')

    char_ids = set()
    for c in chars_elem.findall('char'):
        char_ids.add(int(c.get('id')))

    page_files = [(int(p.get('id')), p.get('file')) for p in pages_elem.findall('page')]

    return {
        'tree': tree,
        'root': root,
        'chars_elem': chars_elem,
        'pages_elem': pages_elem,
        'common_elem': common_elem,
        'char_ids': char_ids,
        'page_files': page_files,
    }


def merge_fonts(base_path, donor_path, out_dir, out_xml_name):
    """Merge donor chars into the base font XML. Donor pages are appended
    with offset so donor glyph references still work via CP-assigned pages."""
    base = parse_font(base_path)
    donor = parse_font(donor_path)

    donor_page_count = len(donor['page_files'])
    # Sort donor pages and assign offset
    donor_page_files_sorted = sorted(donor['page_files'])
    base_page_count = len(base['page_files'])

    # Add donor's pages to base
    for donor_id, donor_file in donor_page_files_sorted:
        new_id = base_page_count + donor_id
        new_page = ET.SubElement(base['pages_elem'], 'page')
        new_page.set('id', str(new_id))
        new_page.set('file', donor_file)

    # Update common.pages
    total_pages = len(base['pages_elem'].findall('page'))
    base['common_elem'].set('pages', str(total_pages))

    # Compute chars missing in base present in donor
    missing_ids = sorted(donor['char_ids'] - base['char_ids'])
    print(f'  base chars: {len(base["char_ids"])}, donor chars: {len(donor["char_ids"])}')
    print(f'  missing to add: {len(missing_ids)}')

    donor_char_map = {int(c.get('id')): c for c in donor['chars_elem'].findall('char')}
    for cid in missing_ids:
        new_char = ET.SubElement(base['chars_elem'], 'char')
        for k, v in donor_char_map[cid].attrib.items():
            if k == 'page':
                new_char.set(k, str(int(v) + base_page_count))
            else:
                new_char.set(k, v)

    total_chars = len(base['chars_elem'].findall('char'))
    base['chars_elem'].set('count', str(total_chars))

    os.makedirs(out_dir, exist_ok=True)
    out_xml = os.path.join(out_dir, out_xml_name)
    base['tree'].write(out_xml, encoding='utf-8', xml_declaration=True)
    print(f'  Saved merged XML: {out_xml}')
    print(f'  Final stats: {total_chars} chars, {total_pages} pages')


def main():
    print('=== Merging Chinese (base) + Japanese (donor) ===')
    merge_fonts(
        os.path.join(ZH_DIR, 'Chinese.xml'),
        os.path.join(JA_DIR, 'Japanese.xml'),
        OUT_ZH,
        'Chinese.xml',
    )

    print('\n=== Merging Japanese (base) + Chinese (donor) ===')
    merge_fonts(
        os.path.join(JA_DIR, 'Japanese.xml'),
        os.path.join(ZH_DIR, 'Chinese.xml'),
        OUT_JA,
        'Japanese.xml',
    )

    print('\nDone! Now pack via xnbcli:')
    print(f'  node xnbcli pack {OUT_ZH}/Chinese.json <out_dir>')
    print(f'  node xnbcli pack {OUT_JA}/Japanese.json <out_dir>')


if __name__ == '__main__':
    main()