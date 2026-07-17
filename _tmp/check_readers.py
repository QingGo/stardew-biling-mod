import json
d = json.load(open('C:/Users/minam/code/stardew-bilin/_tmp/font-zh/SpriteFont1.zh-CN.json', encoding='utf-8'))
for i, r in enumerate(d['readers']):
    t = r['type']
    v = r['version']
    print(f'  {i}: {t} v{v}')
