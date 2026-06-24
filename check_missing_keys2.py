"""
More accurate check: properly handle path mappings and find truly missing keys.
"""
import json
from pathlib import Path

MY_EXPORT_DIR = Path(r"C:\Users\minam\code\stardew-bilin\_export\zh")
TIEBA_FULL_CHR = Path(r"D:\steam\steamapps\common\Stardew Valley\Mods\Tieba Chinese Revision 5.1.2-2936-5-1-2-1762594423\[CP]贴吧中文修订 5.1\assets\full_chr.json")

# Build a proper mapping from export filenames -> CP asset paths
# The export files use underscores, but not always 1:1 with CP asset paths
# We need a lookup table based on the actual files present

EXPORT_OVERRIDES = {
    "Data_Events_BathHouse_Pool.json": "Data/Events/BathHouse_Pool",
    "Data_Events_Trailer.json": "Data/Events/Trailer",
    "Data_Events_Trailer_Big.json": "Data/Events/Trailer_Big",
    "Strings_1_6_Strings.json": "Strings/1_6_Strings",
}

def filename_to_asset_path(filename: str) -> str:
    name = filename[:-5] if filename.endswith(".json") else filename
    # Check overrides first
    if filename in EXPORT_OVERRIDES:
        return EXPORT_OVERRIDES[filename]
    # For normal files: replace all underscores with slashes
    return name.replace("_", "/")

# 1. Load my export data with correct mappings
my_data = {}
my_asset_set = {}
for f in sorted(MY_EXPORT_DIR.iterdir()):
    if not f.name.endswith(".json"):
        continue
    asset_path = filename_to_asset_path(f.name)
    with open(f, encoding="utf-8") as fh:
        raw = json.load(fh)
    my_data[asset_path] = set(raw.keys())
    my_asset_set[asset_path] = raw

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

# 3. Find all keys in Tieba that are NOT in BilingualMod export
# First, overlapping targets
common_targets = sorted(set(my_data.keys()) & set(tieba_data.keys()))

print("=" * 70)
print("Tieba 有但 BilingualMod 导出缺失的 key 统计")
print("（含路径修正后的准确结果）")
print("=" * 70)

total_missing = 0
for target in common_targets:
    my_keys = my_data[target]
    tb_keys = set(tieba_data[target].keys())
    missing = sorted(tb_keys - my_keys)
    if missing:
        total_missing += len(missing)
        print(f"\n--- {target} (缺失 {len(missing)}/{len(tb_keys)} 个 key) ---")
        for k in missing:
            val = tieba_data[target][k][:120]
            print(f"  {k}")
            print(f"    Tieba: {val}")

# 4. Targets Tieba has but my export doesn't have at all
only_tieba = sorted(set(tieba_data.keys()) - set(my_data.keys()))
print(f"\n{'=' * 70}")
print(f"BilingualMod 完全没有导出的 target ({len(only_tieba)} 个):")
print(f"{'=' * 70}")
tb_only_total = 0
for t in only_tieba:
    n = len(tieba_data[t])
    tb_only_total += n
    print(f"  {t}: {n} 个 key")
    for k in list(tieba_data[t].keys())[:5]:
        print(f"    {k}: {tieba_data[t][k][:80]}")
    if len(tieba_data[t]) > 5:
        print(f"    ... 还有 {len(tieba_data[t]) - 5} 个")

print(f"\n{'=' * 70}")
print(f"汇总:")
print(f"  重叠 target 中缺失的 key: {total_missing}")
print(f"  BilingualMod 未覆盖的全新 target: {tb_only_total} 个 key")
print(f"  => 总共 {total_missing + tb_only_total} 个 key 不会出现在双语文本中")
print(f"{'=' * 70}")

# 5. Specifically check: does content.json patch ALL keys that are in the export?
# Or only a subset?
import glob
content_json_path = Path(r"C:\Users\minam\code\stardew-bilin\BilingualMod\content.json")
if content_json_path.exists():
    with open(content_json_path, encoding="utf-8") as f:
        content = json.load(f)
    patched_keys_by_target = {}
    for change in content.get("Changes", []):
        tgt = change.get("Target", "")
        if "Entries" in change:
            if tgt not in patched_keys_by_target:
                patched_keys_by_target[tgt] = set()
            patched_keys_by_target[tgt].update(change["Entries"].keys())
        if "Fields" in change:
            if tgt not in patched_keys_by_target:
                patched_keys_by_target[tgt] = set()
            patched_keys_by_target[tgt].update(change["Fields"].keys())
    
    print(f"\n{'=' * 70}")
    print(f"Content.json 中实际打补丁的情况 vs 导出数据")
    print(f"{'=' * 70}")
    full_miss = 0
    for tgt in sorted(set(tieba_data.keys()) & set(my_asset_set.keys()) - set(patched_keys_by_target.keys())):
        n_tb = len(tieba_data[tgt])
        print(f"  {tgt}: content.json 完全没打补丁, Tieba 有 {n_tb} 个 key")
        full_miss += n_tb
    if full_miss == 0:
        print(f"  (所有 target 在 content.json 中都有补丁)")
    
    for tgt in sorted(common_targets):
        if tgt not in patched_keys_by_target:
            continue
        my_export_keys = set(my_asset_set[tgt].keys())
        patched = patched_keys_by_target[tgt]
        tb_keys = set(tieba_data[tgt].keys())
        not_in_patches = tb_keys - patched
        if not_in_patches:
            print(f"\n  {tgt}: Tieba 有但 content.json 不补丁的 key ({len(not_in_patches)} 个):")
            for k in sorted(not_in_patches)[:5]:
                print(f"    {k}")
