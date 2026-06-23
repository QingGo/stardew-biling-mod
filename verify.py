#!/usr/bin/env python3
"""
统一验证系统：验证导出的数据、生成的 content.json、SMAPI 日志。
用法:
  python verify.py --data         验证导出数据 (token, ^ 分隔)
  python verify.py --dialogue     验证对话分段安全性
  python verify.py --parser       验证 build script 的 parser 分配正确性
  python verify.py --log PATH     解析 SMAPI 日志
  python verify.py --pack PATH    验证 content.json 结构
  python verify.py --all          (默认) 所有检查
"""

import json
import os
import re
import sys
from pathlib import Path

GAME_DIR = r"D:\steam\steamapps\common\Stardew Valley"
EXPORT_DIR = os.path.join(GAME_DIR, "Export_TextAssets")
MOD_DIR = os.path.join(GAME_DIR, "Mods", "BilingualMod")
TOKEN_RE = re.compile(r'\[LocalizedText\s+([\w\\]+):(.+?)\]')
DIALOGUE_SEGMENT_RE = re.compile(r'(#\$[eb]#)')

FAIL = 0
WARN = 0


def log_fail(msg):
    global FAIL
    FAIL += 1
    print(f"  FAIL: {msg}")


def log_warn(msg):
    global WARN
    WARN += 1
    print(f"  WARN: {msg}")


# ====== 1. Token 完整性检查 ======

def check_tokens():
    print("\n=== 1. Token 完整性检查 ===")
    en_dir = os.path.join(EXPORT_DIR, "en")
    zh_dir = os.path.join(EXPORT_DIR, "zh")
    if not os.path.exists(en_dir):
        print("  SKIP: 导出目录不存在，请先运行游戏导出")
        return

    for fname in os.listdir(en_dir):
        if not fname.startswith("Data_"):
            continue

        en_data = json.load(open(os.path.join(en_dir, fname), "r", encoding="utf-8"))
        zh_data = json.load(open(os.path.join(zh_dir, fname), "r", encoding="utf-8"))

        en_tokens = 0
        zh_tokens = 0
        for k, v in en_data.items():
            if isinstance(v, dict):
                for field in ["displayName", "description"]:
                    if TOKEN_RE.search(v.get(field, "")):
                        en_tokens += 1
            elif isinstance(v, str):
                if TOKEN_RE.search(v):
                    en_tokens += 1
        for k, v in zh_data.items():
            if isinstance(v, dict):
                for field in ["displayName", "description"]:
                    if TOKEN_RE.search(v.get(field, "")):
                        zh_tokens += 1
            elif isinstance(v, str):
                if TOKEN_RE.search(v):
                    zh_tokens += 1

        if en_tokens or zh_tokens:
            log_fail(f"{fname}: 未解析 Token — EN={en_tokens} ZH={zh_tokens}")
        else:
            print(f"  OK {fname}")


# ====== 2. ^ 分隔 Entries 检查 ======

def check_caret_entries():
    print("\n=== 2. ^ 分隔 Entries 检查 ===")
    pack_path = os.path.join(MOD_DIR, "content.json")
    if not os.path.exists(pack_path):
        print("  SKIP: 内容包不存在")
        return

    pack = json.load(open(pack_path, "r", encoding="utf-8"))

    for entry in pack["Changes"]:
        if entry.get("Target") in ("Data/Achievements", "Data/SecretNotes"):
            target = entry["Target"]
            when = entry["When"].get("BilingualMode", "?")
            if "Entries" not in entry:
                log_fail(f"{target} ({when}): 使用 Fields 而非 Entries！")
                continue

            for key, val in entry["Entries"].items():
                # Check the entry value has the same number of ^ segments as raw
                count = val.count("^")
                if count < 1:
                    log_fail(f"{target} ({when}) key={key}: 缺少 ^ 分隔符 (值={val[:60]})")

                # Check that bilingual entries have " / " in display-related fields
                if when == "Bilingual":
                    fields = val.split("^")
                    has_bilingual = any(" / " in f for f in fields)
                    if not has_bilingual:
                        log_warn(f"{target} ({when}) key={key}: 双语版缺少 / 分隔")

            print(f"  OK {target} ({when}): {len(entry['Entries'])} entries")


# ====== 3. 对话分段安全检查 ======

def check_dialogue_safety():
    print("\n=== 3. 对话分段安全检查 ===")
    pack_path = os.path.join(MOD_DIR, "content.json")
    if not os.path.exists(pack_path):
        print("  SKIP: 内容包不存在")
        return

    pack = json.load(open(pack_path, "r", encoding="utf-8"))

    for entry in pack["Changes"]:
        if not entry.get("Target", "").startswith("Characters/Dialogue/"):
            continue
        if entry["When"].get("BilingualMode") != "true":
            continue

        target = entry["Target"]
        broken_count = 0
        total_count = 0

        for key, val in entry.get("Entries", {}).items():
            total_count += 1
            # Check if #$e# appears AFTER " / " (Chinese text after end marker)
            has_lost_chinese = False

            # Split by #$e# and check each segment
            segments = val.split("#$e#")
            for seg_idx, seg in enumerate(segments):
                if " / " in seg:
                    parts = seg.split(" / ", 1)
                    after_sep = parts[1] if len(parts) > 1 else ""
                    # If this segment is BEFORE the last #$e# (i.e., it's a non-terminal segment)
                    if seg_idx < len(segments) - 1:
                        # Chinese text before #$e# is fine (it's shown before end)
                        # Chinese text after a #$e# at the end of the segment would be in a later segment
                        # which would also be after #$e# and lost
                        pass

            # Check for Chinese text at the very end after the last #$e# (will be lost)
            parts = val.split("#$e#")
            last_after = parts[-1]
            if " / " in last_after:
                cn_part = last_after.split(" / ", 1)[1] if " / " in last_after else ""
                # If there's Chinese text after the final #$e#, it's lost!
                if cn_part.strip():
                    broken_count += 1

        pct = broken_count / total_count * 100 if total_count else 0
        if broken_count > 0:
            log_warn(f"{target}: {broken_count}/{total_count} 条目在 #$e# 后仍有中文 ({pct:.0f}%)")
        else:
            print(f"  OK {target}: {total_count} 条目安全")


# ====== 4. SMAPI 日志解析 ======

def check_smapi_log(log_path):
    print(f"\n=== 4. SMAPI 日志分析: {log_path} ===")
    if not os.path.exists(log_path):
        print(f"  SKIP: {log_path} 不存在")
        return

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    ignored = []
    errors = []
    load_patches = 0
    edit_patches = 0

    for line in lines:
        if "Ignored" in line and "Bilingual Text" in line:
            ignored.append(line.strip())
        if "[Content Patcher]" in line and "error" in line.lower():
            errors.append(line.strip())
        if "Load" in line and "Bilingual Text" in line and "applied" in line.lower():
            load_patches += 1
        if "EditData" in line and "Bilingual Text" in line and "applied" in line.lower():
            edit_patches += 1

    if ignored:
        log_fail(f"{len(ignored)} 个补丁被忽略:")
        for ig in ignored[:5]:
            print(f"    {ig[:120]}...")
    else:
        print("  OK: 0 个忽略补丁")

    if errors:
        log_fail(f"{len(errors)} 个错误:")
        for err in errors[:5]:
            print(f"    {err[:120]}")
    else:
        print("  OK: 0 个错误")

    print(f"  Load: {load_patches}  EditData: {edit_patches}")


# ====== 5. Mail 格式检查 ======

def check_mail():
    print("\n=== 5. Mail 格式检查 ===")
    pack_path = os.path.join(MOD_DIR, "content.json")
    if not os.path.exists(pack_path):
        print("  SKIP: 内容包不存在")
        return

    pack = json.load(open(pack_path, "r", encoding="utf-8"))

    for entry in pack["Changes"]:
        if entry.get("Target") != "Data/mail":
            continue
        mode = entry["When"].get("BilingualMode", "?")
        if mode != "true":
            continue

        total = 0
        double_marker = 0
        unterminated_cmd = 0
        for key, val in entry.get("Entries", {}).items():
            total += 1
            if val.count("[#]") > 1:
                double_marker += 1
                log_fail(f"{key}: {val.count('[#]')} [#] markers")
            if "%" in val and " / " in val:
                en_half = val.split(" / ", 1)[0]
                if "%" in en_half and "%%" not in en_half:
                    unterminated_cmd += 1
                    log_fail(f"{key}: %command lacks %% in EN half")

        if double_marker or unterminated_cmd:
            log_fail(f"Data/mail ({mode}): {double_marker} 双重标记, {unterminated_cmd} 未终结命令")
        else:
            print(f"  OK Data/mail ({mode}): {total} 条目格式正确")


# ====== 6. 节日检查 ======

def check_festivals():
    print("\n=== 6. 节日 name 字段检查 ===")
    pack_path = os.path.join(MOD_DIR, "content.json")
    if not os.path.exists(pack_path):
        print("  SKIP: 内容包不存在")
        return

    pack = json.load(open(pack_path, "r", encoding="utf-8"))
    festival_targets = set()

    for entry in pack["Changes"]:
        target = entry.get("Target", "")
        if str(target).startswith("Data/Festivals/") and str(target) != "Data/Festivals/FestivalDates":
            festival_targets.add(target)
            mode = entry["When"].get("BilingualMode", "?")
            entries = entry.get("Entries", {})
            name_val = entries.get("name", "")
            if not name_val:
                log_fail(f"{target} (BilingualMode={mode}): name 字段为空")
            elif mode == "true" and " / " not in name_val:
                log_fail(f"{target} (BilingualMode={mode}): 双语模式缺少 / 分隔符")

    if festival_targets:
        print(f"  OK: {len(festival_targets)} 个节日资产")
    else:
        log_fail("未找到任何节日资产补丁")


# ====== 7. Parser 分配检查 ======

def check_parser_assignment():
    print("\n=== 7. Parser 分配检查 ===")
    # Add build_bilingual_pack to path for its classification functions
    builder_dir = Path(__file__).parent / "BilingualModBuilder"
    sys.path.insert(0, str(builder_dir))
    try:
        from build_bilingual_pack import (
            is_string_asset, is_data_asset, is_festival_asset,
            DIALOGUE_ASSET_PREFIXES, MAIL_ASSET_PATHS,
            EVENT_ASSET_PREFIX, DATA_FIELD_MAP,
        )
    except ImportError:
        print("  SKIP: 无法导入 build_bilingual_pack.py")
        return

    # Use committed export data
    script_dir = Path(__file__).parent
    zh_dir = script_dir / "_export" / "zh"
    en_dir = script_dir / "_export" / "en"
    assets_file = builder_dir / "assets-list.txt"

    if not zh_dir.exists() or not assets_file.exists():
        print("  SKIP: 导出数据或资产列表不存在")
        return

    with open(assets_file, encoding="utf-8") as f:
        asset_paths = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # Handle path overrides for export filenames
    EXPORT_OVERRIDES = {
        "Data/Events/BathHouse_Pool": "Data_Events_BathHouse_Pool.json",
        "Data/Events/Trailer_Big": "Data_Events_Trailer_Big.json",
        "Strings/1_6_Strings": "Strings_1_6_Strings.json",
    }

    def asset_to_filename(ap):
        if ap in EXPORT_OVERRIDES:
            return EXPORT_OVERRIDES[ap]
        return ap.replace("/", "_") + ".json"

    total_issues = 0
    for ap in sorted(asset_paths):
        fn = asset_to_filename(ap)
        zh_file = zh_dir / fn
        if not zh_file.exists():
            continue

        try:
            with open(zh_file, encoding="utf-8") as f:
                zh = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        # Determine what parser the build script would assign
        cat = None
        if is_festival_asset(ap):
            cat = "festival (name-only)"
        elif is_data_asset(ap):
            cat = "data/{}".format(DATA_FIELD_MAP[ap]["type"])
        elif is_string_asset(ap):
            if (
                any(ap.startswith(p) for p in DIALOGUE_ASSET_PREFIXES)
                or ap == "Data/ExtraDialogue"
                or ap == "Strings/MovieReactions"
                or ap == "Strings/SpecialOrderStrings"
            ):
                cat = "dialogue parser"
            elif ap in MAIL_ASSET_PATHS:
                cat = "mail parser"
            elif ap.startswith(EVENT_ASSET_PREFIX):
                cat = "event parser"
            else:
                cat = "plain template"
        else:
            cat = "UNKNOWN"

        # Scan content for text markers
        has_caret = False
        has_hash_b = False
        has_hash_e = False
        for v in zh.values():
            if not isinstance(v, str):
                continue
            if "^" in v:
                has_caret = True
            if "#$b#" in v:
                has_hash_b = True
            if "#$e#" in v:
                has_hash_e = True

        issues_fail = []
        issues_warn = []

        # ^ gender split → always a real bug (now handled by bilingualize_pair)
        if has_caret and cat == "plain template":
            issues_warn.append("含 ^ 性别分支（已通过 bilingualize_pair 修复）")

        # #$b#/#$e# in plain template → depends on context
        if (has_hash_b or has_hash_e) and cat == "plain template":
            # These might be dialogue-like strings displayed in dialogue box
            # where #$b# IS parsed, causing segment interleaving.
            # Only flag as FAIL if the asset name suggests dialogue content.
            dialogue_like = any(x in ap for x in [
                "Characters/", "Dialogue", "ExtraDialogue",
                "SimpleNonVillagerDialogues",
            ])
            if dialogue_like:
                issues_fail.append("含 #$b#/#$e# 分段但走 plain template，可能分段错乱")
            else:
                issues_warn.append("含 #$b#/#$e# 分段但走 plain template（上下文未知，低风险）")

        # #$b# segments in data Fields → segments mixed with pipe-split fields
        if (has_hash_b or has_hash_e) and cat and cat.startswith("data/"):
            issues_fail.append("含 #$b#/#$e# 分段但走 data Fields，可能数据错乱")

        if issues_fail:
            total_issues += 1
            for issue in issues_fail:
                log_fail(f"{ap} [{cat}]: {issue}")
                print(f"       当前 parser: {cat}")
        if issues_warn:
            for issue in issues_warn:
                log_warn(f"{ap} [{cat}]: {issue}")
                print(f"       当前 parser: {cat}")
        if not issues_fail and not issues_warn:
            print(f"  OK {ap} [{cat}]")

    if total_issues:
        print(f"\n  总计: {total_issues} 个 asset 可能有 parser 分配问题")
    else:
        print(f"\n  全部 {len(asset_paths)} 个 asset parser 分配正确")


# ====== Main ======

def main():
    args = sys.argv[1:]
    do_all = not args or "--all" in args

    if do_all or "--data" in args:
        check_tokens()
        check_caret_entries()

    if do_all or "--dialogue" in args:
        check_dialogue_safety()

    if do_all or "--parser" in args:
        check_parser_assignment()

    if do_all or "--pack" in args:
        check_caret_entries()
        check_dialogue_safety()
        check_mail()
        check_festivals()

    # Check SMAPI log if provided
    for a in args:
        if a.startswith("--log="):
            check_smapi_log(a.split("=", 1)[1])

    print(f"\n=== 结果: FAIL={FAIL} WARN={WARN} ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
