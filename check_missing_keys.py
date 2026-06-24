"""
Check which keys Tieba has but BilingualMod's export doesn't cover.
These would be missed for bilingualization if both mods run together.
"""
import json
from pathlib import Path

MY_EXPORT_DIR = Path(r"C:\Users\minam\code\stardew-bilin\_export\zh")
TIEBA_FULL_CHR = Path(r"D:\steam\steamapps\common\Stardew Valley\Mods\Tieba Chinese Revision 5.1.2-2936-5-1-2-1762594423\[CP]贴吧中文修订 5.1\assets\full_chr.json")

def filename_to_asset_path(filename: str) -> str:
    name = filename[:-5] if filename.endswith(".json") else filename
    return name.replace("_", "/")

# 1. Load my export data
my_data = {}
for f in sorted(MY_EXPORT_DIR.iterdir()):
    if not f.name.endswith(".json"):
        continue
    asset_path = filename_to_asset_path(f.name)
    with open(f, encoding="utf-8") as fh:
        raw = json.load(fh)
    my_data[asset_path] = set(raw.keys())

# 2. Load Tieba data
with open(TIEBA_FULL_CHR, encoding="utf-8") as f:
    tieba_raw = json.load(f)

tieba_data = {}
for change in tieba_raw["Changes"]:
    if change.get("Action") != "EditData":
        continue
    target = change["Target"]
    entries = change.get("Entries", {})
    if target not in tieba_data:
        tieba_data[target] = {}
    tieba_data[target].update(entries)

# 3. Find keys Tieba has but my export doesn't
common_targets = sorted(set(my_data.keys()) & set(tieba_data.keys()))

print(f"{'='*70}")
print(f"Tieba 有但 BilingualMod 导出缺失的 key 统计")
print(f"{'='*70}")

total_missing = 0
missing_details = []

for target in common_targets:
    my_keys = my_data[target]
    tb_keys = set(tieba_data[target].keys())
    missing = sorted(tb_keys - my_keys)
    if missing:
        total_missing += len(missing)
        missing_details.append((target, missing))
        print(f"\n--- {target} (缺失 {len(missing)} 个 key) ---")
        for k in missing[:10]:
            print(f"  {k}")
            print(f"    Tieba 文本: {tieba_data[target][k][:100]}")
        if len(missing) > 10:
            print(f"  ... 还有 {len(missing) - 10} 个")

print(f"\n{'='*70}")
print(f"总计: {total_missing} 个 key 在 Tieba 中有但在 BilingualMod 导出中缺失")
print(f"{'='*70}")

# Also check: targets Tieba patches that my mod doesn't even target
only_tieba_targets = sorted(set(tieba_data.keys()) - set(my_data.keys()))
if only_tieba_targets:
    tb_only_keys = sum(len(tieba_data[t]) for t in only_tieba_targets)
    print(f"\nTieba 有但 BilingualMod 完全不处理的 target ({len(only_tieba_targets)} 个):")
    for t in only_tieba_targets:
        print(f"  - {t} ({len(tieba_data[t])} 个 key)")
    print(f"  这些 target 共 {tb_only_keys} 个 key 完全不会双语化")
    total_missing += tb_only_keys

print(f"\n最终: 共 {total_missing} 个 key 的汉文不会出现在双语文本中")
