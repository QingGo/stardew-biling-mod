import xml.etree.ElementTree as ET

paths = [
    ('Chinese.xml', 'C:/Users/minam/code/stardew-bilin/_tmp/font-zh-bmf/Chinese.xml'),
    ('Japanese.xml', 'C:/Users/minam/code/stardew-bilin/_tmp/font-ja-bmf/Japanese.xml'),
    ('Merged Chinese.xml', 'C:/Users/minam/code/stardew-bilin/_tmp/font-zh-bmf-merged/Chinese.xml'),
    ('Merged Japanese.xml', 'C:/Users/minam/code/stardew-bilin/_tmp/font-ja-bmf-merged/Japanese.xml'),
]
for label, path in paths:
    print(f'=== {label} ===')
    tree = ET.parse(path)
    root = tree.getroot()
    info = root.find('info')
    common = root.find('common')
    print('info face:', info.get('face'), 'size:', info.get('size'))
    print('common scaleW:', common.get('scaleW'), 'scaleH:', common.get('scaleH'))
    print('common lineHeight:', common.get('lineHeight'), 'base:', common.get('base'))
    pages = root.find('pages')
    for p in pages.findall('page'):
        print('page id:', p.get('id'), 'file:', p.get('file'))
    print()