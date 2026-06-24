"""
Compare BilingualMod's official Chinese export against Tieba Chinese Revision
to find text conflicts.
"""
import json
import os
import re
from pathlib import Path

MY_EXPORT_DIR = Path(r"C:\Users\minam\code\stardew-bilin\_export\zh")
TIEBA_FULL_CHR = Path(r"D:\steam\steamapps\common\Stardew Valley\Mods\Tieba Chinese Revision 5.1.2-2936-5-1-2-1762594423\[CP]贴吧中文修订 5.1\assets\full_chr.json")

# ── 1. Load my export data ──────────────────────────────────

def filename_to_asset_path(filename: str) -> str:
    """Convert Characters_Dialogue_Abigail.json -> Characters/Dialogue/Abigail"""
    name = filename[:-5] if filename.endswith(".json") else filename
    return name.replace("_", "/")

def load_my_exports():
    """Load all zh export files into dict: {asset_path: {key: text}}"""
    data = {}
    for f in sorted(MY_EXPORT_DIR.iterdir()):
        if not f.name.endswith(".json"):
            continue
        asset_path = filename_to_asset_path(f.name)
        with open(f, encoding="utf-8") as fh:
            raw = json.load(fh)
        # Flatten: if values are dicts (structured data), join fields
        entries = {}
        for key, val in raw.items():
            if isinstance(val, dict):
                # structured: {"displayName": "...", "description": "..."}
                texts = []
                for field_name in ("description", "displayName", "name", "title"):
                    if field_name in val:
                        texts.append(val[field_name])
                if texts:
                    entries[key] = " | ".join(texts)
            elif isinstance(val, str):
                entries[key] = val
            else:
                entries[key] = str(val)
        data[asset_path] = entries
    return data

# ── 2. Load Tieba data ──────────────────────────────────────

def load_tieba_data():
    """Parse full_chr.json into dict: {asset_path: {key: text}}"""
    with open(TIEBA_FULL_CHR, encoding="utf-8") as f:
        raw = json.load(f)
    data = {}
    for change in raw["Changes"]:
        if change.get("Action") != "EditData":
            continue
        target = change["Target"]
        entries = change.get("Entries", {})
        if not entries:
            continue
        if target not in data:
            data[target] = {}
        data[target].update(entries)
    return data

# ── 3. Compare ──────────────────────────────────────────────

def extract_chinese(text: str) -> str:
    """Extract meaningful Chinese characters for comparison.
    Strip English parts, CP tokens, and clean whitespace."""
    # Remove CP tokens like {{Random: ...}}
    text = re.sub(r'\{\{.*?\}\}', '', text)
    # Keep only Chinese characters, basic punctuation
    chinese_only = re.findall(r'[\u4e00-\u9fff\u3000-\u3037\uff00-\uffef\w\d\s]', text)
    return ''.join(chinese_only).strip()

def main():
    my_data = load_my_exports()
    tieba_data = load_tieba_data()

    print(f"BilingualMod export targets: {len(my_data)}")
    print(f"Tieba revision targets: {len(tieba_data)}")

    # Find overlapping targets
    common_targets = sorted(set(my_data.keys()) & set(tieba_data.keys()))
    only_my = sorted(set(my_data.keys()) - set(tieba_data.keys()))
    only_tieba = sorted(set(tieba_data.keys()) - set(my_data.keys()))

    print(f"\n重叠的目标 (shared targets): {len(common_targets)}")
    print(f"只有 BilingualMod 有的目标: {len(only_my)}")
    print(f"只有 Tieba 有的目标: {len(only_tieba)}")

    if only_my:
        print(f"\n只有 BilingualMod 的目标:")
        for t in only_my:
            print(f"  - {t} ({len(my_data[t])} 条目)")

    if only_tieba:
        print(f"\n只有 Tieba 的目标:")
        for t in only_tieba:
            print(f"  - {t} ({len(tieba_data[t])} 条目)")

    # Compare overlapping entries
    total_conflicts = 0
    total_overlap_keys = 0
    conflicts_detail = {}  # target -> [(key, my_text, tieba_text)]

    for target in common_targets:
        my_entries = my_data[target]
        tb_entries = tieba_data[target]
        common_keys = sorted(set(my_entries.keys()) & set(tb_entries.keys()))
        total_overlap_keys += len(common_keys)

        for key in common_keys:
            my_text = extract_chinese(my_entries[key])
            tb_text = extract_chinese(tb_entries[key])

            # Only compare the Chinese portion
            # Get Chinese chars from both
            my_zh = re.findall(r'[\u4e00-\u9fff]+', my_text)
            tb_zh = re.findall(r'[\u4e00-\u9fff]+', tb_text)
            my_zh_str = ''.join(my_zh)
            tb_zh_str = ''.join(tb_zh)

            if my_zh_str != tb_zh_str:
                total_conflicts += 1
                if target not in conflicts_detail:
                    conflicts_detail[target] = []
                # Store first 5 per target
                if len(conflicts_detail[target]) < 5:
                    conflicts_detail[target].append((key, my_entries[key], tb_entries[key]))

    print(f"\n{'='*60}")
    print(f"=== 对比结果 ===")
    print(f"{'='*60}")
    print(f"重叠的条目总数 (shared entry keys): {total_overlap_keys}")
    print(f"有冲突的条目数 (different Chinese text): {total_conflicts}")
    if total_overlap_keys > 0:
        print(f"冲突率: {total_conflicts / total_overlap_keys * 100:.1f}%")

    if total_conflicts == 0:
        print("\n两个mod的汉文内容完全一致，没有冲突！")
        return

    # ── Show examples ──
    print(f"\n{'='*60}")
    print(f"=== 冲突示例 ===")
    print(f"{'='*60}")

    example_count = 0
    for target in sorted(conflicts_detail.keys()):
        examples = conflicts_detail[target]
        total_for_target = sum(
            1 for k in set(my_data[target].keys()) & set(tieba_data[target].keys())
            if extract_chinese(my_data[target][k]) != extract_chinese(tieba_data[target][k])
        )
        print(f"\n--- {target} (共 {total_for_target} 处冲突) ---")
        for key, my_val, tb_val in examples:
            if example_count >= 30:
                break
            example_count += 1
            print(f"  key: {key}")
            print(f"    官方: {my_val[:120]}")
            print(f"    贴吧: {tb_val[:120]}")
            print()

    # Summary by target
    print(f"{'='*60}")
    print(f"=== 按目标统计冲突分布 ===")
    print(f"{'='*60}")
    for target in sorted(conflicts_detail.keys()):
        total_for_target = sum(
            1 for k in set(my_data[target].keys()) & set(tieba_data[target].keys())
            if extract_chinese(my_data[target][k]) != extract_chinese(tieba_data[target][k])
        )
        total_keys = len(set(my_data[target].keys()) & set(tieba_data[target].keys()))
        print(f"  {target}: {total_for_target}/{total_keys} ({total_for_target/total_keys*100:.0f}%)")


if __name__ == "__main__":
    main()
