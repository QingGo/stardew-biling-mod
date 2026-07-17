"""
Fix the merged font JSON: set texture format to 0 (Color/BGRA32)
so xnbcli writes uncompressed pixels (no DXT required).
"""
import json

json_path = 'C:/Users/minam/code/stardew-bilin/_tmp/font-zh/SpriteFont1.zh-CN.json'

data = json.load(open(json_path, encoding='utf-8'))

# Change from DXT3 (5) to Color (0) - uncompressed BGRA32
old_fmt = data['content']['texture']['format']
data['content']['texture']['format'] = 0
print(f'Format: {old_fmt} -> 0 (Color/BGRA32)')

json.dump(data, open(json_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('JSON updated')
