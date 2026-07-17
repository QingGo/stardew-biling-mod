import argparse
import json
import os
import shutil
from pathlib import Path

from parsers import (
    BILINGUAL_TEMPLATE,
    bilingualize_pair,
    bilingualize_event_quoted_text,
    make_dialogue_bilingual,
    make_mail_bilingual,
    make_event_bilingual,
)

# ====== Festival command detection ======
FESTIVAL_CMD_PATTERNS = ("speak ", "pause ", "move ", "jump ", "warp ")  # for classifying festival entries

# ====== Config ======
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_EXPORT_DIR = SCRIPT_DIR.parent / "_export"  # committed export data for CI
GAME_EXPORT_DIR = Path("D:/steam/steamapps/common/Stardew Valley/Export_TextAssets")
OUTPUT_DIR = Path("./BilingualMod")
ASSETS_LIST_FILE = Path("./assets-list.txt")

PIPE_BILINGUAL_TEMPLATE = "{left} | {right}"

EXPORT_DIR = None  # set by main() via CLI arg or auto-detect

# Data/* 资产的字段映射
#   model: 模型型 (named fields), 用 EditData + Fields
#   pipe:  管道分隔型 (/ 分割), 用 EditData + Fields
#   caret: ^ 分隔型 (int key), 用 EditData + Entries 全值替换
DATA_FIELD_MAP = {
    "Data/Objects":   { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/Tools":     { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/Weapons":   { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/Shirts":    { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/Pants":     { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/BigCraftables": { "type": "model", "displayName": "DisplayName", "description": "Description" },
    "Data/Powers":    { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/Trinkets":  { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/hats":      { "type": "pipe",   "displayName": 5, "description": 1 },
    "Data/Boots":     { "type": "pipe",   "displayName": 6, "description": 1 },
    "Data/Quests":    { "type": "pipe",   "displayName": 1, "description": 2 },
    "Data/EngagementDialogue": { "type": "pipe", "displayName": 0, "description": 1 },
    "Data/SecretNotes":  { "type": "caret", "delimiter": "^", "displayName": 0, "description": 1 },
    "Data/Achievements": { "type": "caret", "delimiter": "^", "displayName": 0, "description": 1 },
    "Data/Bundles":   { "type": "pipe", "displayName": 6, "description": None },
    "Data/Monsters":  { "type": "pipe", "displayName": 14, "description": None },
    "Data/NPCGiftTastes": { "type": "pipe_multi", "textFields": [0, 2, 4, 6, 8], "delimiter": "/" },
}

# 只处理字符串类型的资产前缀（不生成 EditData Fields）
STRING_ASSET_PREFIXES = ["Strings/", "Characters/Dialogue/"]

DIALOGUE_ASSET_PREFIXES = ["Characters/Dialogue/"]
MAIL_ASSET_PATHS = ["Data/mail"]
EVENT_ASSET_PREFIX = "Data/Events/"
FESTIVAL_ASSET_PREFIX = "Data/Festivals/"


def asset_path_to_filename(asset_path: str) -> str:
    return asset_path.replace("/", "_").replace("\\", "_") + ".json"


def load_json(file_path: Path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_string_asset(asset_path: str) -> bool:
    """判断是否为纯文本 Dict<string,string> 类型资产"""
    return any(asset_path.startswith(p) for p in STRING_ASSET_PREFIXES) or asset_path in [
        "Data/ExtraDialogue", "Data/mail",
        "Data/TV/CookingChannel", "Data/TV/TipChannel",
        "Data/Festivals/FestivalDates"
    ] or asset_path.startswith(EVENT_ASSET_PREFIX)


def is_data_asset(asset_path: str) -> bool:
    """判断是否为 Data/* 结构化资产"""
    return asset_path in DATA_FIELD_MAP


def is_festival_asset(asset_path: str) -> bool:
    return asset_path.startswith(FESTIVAL_ASSET_PREFIX) and not asset_path.endswith("FestivalDates")


def main():
    parser = argparse.ArgumentParser(description="Build bilingual Content Patcher pack")
    parser.add_argument("--export-dir", type=str, default=None,
                        help="Path to Export_TextAssets (default: auto-detect)")
    parser.add_argument("--pairs", type=str, nargs="+", default=["en:zh"],
                        help="Language pairs: lang1:lang2 lang1:lang2 ... (default: en:zh)")
    args = parser.parse_args()

    # Check for font-limited pairs
    font_limited = {"ja:zh", "zh:ja", "ko:zh", "zh:ko", "ja:ko", "ko:ja"}
    for pair in args.pairs:
        if pair in font_limited:
            print(f"注意：语言对 {pair} 的两种文字使用不同的位图字体（SpriteFont），")
            print(f"      游戏引擎无法同时渲染两种非拉丁字符集。")
            print(f"      共享的 CJK 汉字可以正常显示，但日文假名/韩文谚文会显示为 *。")
            print(f"      如需完整支持，需要安装自定义合并字体的 Mod (外部工具制作 XNB)。")
            print()

    # Auto-detect export dir: game path first, fall back to committed _export
    global EXPORT_DIR
    if args.export_dir:
        EXPORT_DIR = Path(args.export_dir)
    elif GAME_EXPORT_DIR.exists():
        EXPORT_DIR = GAME_EXPORT_DIR
    else:
        EXPORT_DIR = DEFAULT_EXPORT_DIR

    if not ASSETS_LIST_FILE.exists():
        print(f"错误：找不到资产列表文件 {ASSETS_LIST_FILE}")
        return

    with open(ASSETS_LIST_FILE, 'r', encoding='utf-8') as f:
        asset_paths = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    content_changes = []
    all_pair_codes = []

    for pair in args.pairs:
        lang1, lang2 = pair.split(':')
        pair_code = f"{lang1}-{lang2}"
        all_pair_codes.append(pair_code)
        when_val = pair_code

        # (v2.0.0: removed "true" backward-compat — CP validates ALL When
        #  values against AllowValues, so "true" outside AllowValues causes
        #  validation warnings for every patch.)
        for asset_path in asset_paths:
            filename = asset_path_to_filename(asset_path)
            lang1_file = EXPORT_DIR / lang1 / filename
            lang2_file = EXPORT_DIR / lang2 / filename

            if not lang1_file.exists():
                print(f"警告：缺失 {lang1} 资产 {asset_path}（查找路径：{lang1_file}），跳过")
                continue

            if is_festival_asset(asset_path):
                if not lang2_file.exists():
                    print(f"警告：缺失 {lang2} 节日资产 {asset_path}，跳过")
                    continue
                lang1_data = load_json(lang1_file)
                lang2_data = load_json(lang2_file)
                name1 = lang1_data.get("name", "")
                name2 = lang2_data.get("name", "")
                if not name1:
                    print(f"警告：节日 {asset_path} 缺少 name 字段，跳过")
                    continue

                entries = {}
                entries["name"] = BILINGUAL_TEMPLATE.format(left=name1, right=name2) if name2 else name1

                for key in lang1_data:
                    if key == "name":
                        continue
                    v1 = lang1_data.get(key, "")
                    v2 = lang2_data.get(key, "")
                    if not v1 or v1 == v2:
                        continue
                    if "/" in v1 and any(cmd in v1 for cmd in FESTIVAL_CMD_PATTERNS):
                        entries[key] = make_event_bilingual(v1, v2)
                    else:
                        entries[key] = make_dialogue_bilingual(v1, v2)

                content_changes.append({
                    "Action": "EditData",
                    "Target": asset_path,
                    "When": {"BilingualMode": when_val},
                    "Entries": entries
                })

            elif is_string_asset(asset_path):
                if not lang2_file.exists():
                    print(f"警告：缺失 {lang2} 资产 {asset_path}，将使用 {lang1} 代替")
                    lang2_data = None
                else:
                    lang2_data = load_json(lang2_file)

                lang1_data = load_json(lang1_file)

                all_keys = set(lang1_data.keys())
                if lang2_data:
                    all_keys |= set(lang2_data.keys())

                is_dialogue = (
                    any(asset_path.startswith(p) for p in DIALOGUE_ASSET_PREFIXES)
                    or asset_path == "Data/ExtraDialogue"
                    or asset_path == "Strings/MovieReactions"
                    or asset_path == "Strings/SpecialOrderStrings"
                    or asset_path == "Strings/StringsFromCSFiles"
                    or asset_path == "Strings/1_6_Strings"
                    or asset_path == "Strings/StringsFromMaps"
                    or asset_path == "Strings/SimpleNonVillagerDialogues"
                )
                is_mail = asset_path in MAIL_ASSET_PATHS
                is_event = asset_path.startswith(EVENT_ASSET_PREFIX)
                is_cooking = asset_path == "Data/TV/CookingChannel"

                bilingual_data = {}
                for key in all_keys:
                    v1 = lang1_data.get(key, "")
                    v2 = lang2_data.get(key, "") if lang2_data else ""

                    if is_mail:
                        bilingual_data[key] = make_mail_bilingual(v1, v2)
                    elif is_event:
                        bilingual_data[key] = make_event_bilingual(v1, v2)
                    elif is_dialogue:
                        bilingual_data[key] = make_dialogue_bilingual(v1, v2)
                    elif is_cooking:
                        if '/' in v1 and '/' in v2:
                            recipe_name, d1 = v1.split('/', 1)
                            _, d2 = v2.split('/', 1)
                            bilingual_data[key] = f"{recipe_name}/{bilingualize_pair(d1, d2)}"
                        else:
                            bilingual_data[key] = bilingualize_pair(v1, v2)
                    else:
                        if v1 and v2:
                            if '$q' in v1 and '$q' in v2:
                                bilingual_data[key] = bilingualize_event_quoted_text(v1, v2)
                            elif '$y' in v1 and '$y' in v2:
                                bilingual_data[key] = bilingualize_event_quoted_text(v1, v2)
                            elif '#$b#' in v1 or '#$b#' in v2 or '#$e#' in v1 or '#$e#' in v2:
                                bilingual_data[key] = make_dialogue_bilingual(v1, v2)
                            else:
                                bilingual_data[key] = bilingualize_pair(v1, v2)
                        elif v1:
                            bilingual_data[key] = f"{v1} / "
                        elif v2:
                            bilingual_data[key] = f" / {v2}"
                        else:
                            bilingual_data[key] = ""

                content_changes.append({
                    "Action": "EditData",
                    "Target": asset_path,
                    "When": { "BilingualMode": when_val },
                    "Entries": bilingual_data
                })

            elif is_data_asset(asset_path):
                if not lang2_file.exists():
                    print(f"警告：缺失 {lang2} Data 资产 {asset_path}，跳过")
                    continue

                lang1_data = load_json(lang1_file)
                lang2_data = load_json(lang2_file)

                field_map = DATA_FIELD_MAP[asset_path]
                asset_type = field_map["type"]

                if asset_type == "pipe_multi":
                    delimiter = field_map.get("delimiter", "/")
                    text_fields = field_map["textFields"]
                    bi_sep = PIPE_BILINGUAL_TEMPLATE
                    bi_fields_data = {}

                    all_keys = set(lang1_data.keys()) | set(lang2_data.keys())
                    for key in all_keys:
                        item1 = lang1_data.get(key, {})
                        item2 = lang2_data.get(key, {})

                        raw1 = item1.get("_raw", "") if isinstance(item1, dict) else ""
                        raw2 = item2.get("_raw", "") if isinstance(item2, dict) else ""

                        if not raw1 or not raw2:
                            dn1 = item1.get("displayName", "") if isinstance(item1, dict) else ""
                            dn2 = item2.get("displayName", "") if isinstance(item2, dict) else ""
                            if dn1 and dn2:
                                bi_fields_data[key] = {str(text_fields[0]): bi_sep.format(left=dn1, right=dn2)}
                            continue

                        fields1 = raw1.split(delimiter)
                        fields2 = raw2.split(delimiter)

                        field_vals = {}
                        for idx in text_fields:
                            f1 = fields1[idx] if idx < len(fields1) else ""
                            f2 = fields2[idx] if idx < len(fields2) else ""
                            if f1 and f2:
                                field_vals[str(idx)] = bi_sep.format(left=f1, right=f2)
                            elif f1:
                                field_vals[str(idx)] = f"{f1} | "
                            elif f2:
                                field_vals[str(idx)] = f" | {f2}"
                        if field_vals:
                            bi_fields_data[key] = field_vals

                    if bi_fields_data:
                        content_changes.append({
                            "Action": "EditData",
                            "Target": asset_path,
                            "When": {"BilingualMode": when_val},
                            "Fields": bi_fields_data
                        })
                    continue

                dn_field = field_map["displayName"]
                desc_field = field_map["description"]
                sep = PIPE_BILINGUAL_TEMPLATE if asset_type == "pipe" else BILINGUAL_TEMPLATE

                if asset_type == "caret":
                    delimiter = field_map.get("delimiter", "^")
                    bi_entries = {}

                    all_keys = set(lang1_data.keys()) | set(lang2_data.keys())
                    for key in all_keys:
                        item1 = lang1_data.get(key, {})
                        item2 = lang2_data.get(key, {})

                        if not isinstance(item1, dict):
                            item1 = {"_raw": str(item1), "displayName": str(item1), "description": ""}
                        if not isinstance(item2, dict):
                            item2 = {"_raw": str(item2), "displayName": str(item2), "description": ""}

                        raw1 = item1.get("_raw", "")
                        raw2 = item2.get("_raw", "")

                        if not raw1 and not raw2:
                            continue

                        if raw1 or raw2:
                            fields1 = raw1.split(delimiter) if raw1 else []
                            fields2 = raw2.split(delimiter) if raw2 else []
                            max_len = max(len(fields1), len(fields2))
                            bi_fields = [""] * max_len
                            for i in range(max_len):
                                f1 = fields1[i] if i < len(fields1) else ""
                                f2 = fields2[i] if i < len(fields2) else ""
                                if i in (dn_field, desc_field) and f1 and f2:
                                    bi_fields[i] = f"{f1} / {f2}"
                                elif i in (dn_field, desc_field) and f1 and not f2:
                                    bi_fields[i] = f"{f1} / "
                                elif i in (dn_field, desc_field) and not f1 and f2:
                                    bi_fields[i] = f" / {f2}"
                                else:
                                    if f1 and f2 and f1 != f2:
                                        bi_fields[i] = f"{f1} / {f2}"
                                    else:
                                        bi_fields[i] = f1 or f2
                            bi_entries[key] = delimiter.join(bi_fields)

                    if bi_entries:
                        content_changes.append({
                            "Action": "EditData",
                            "Target": asset_path,
                            "When": {"BilingualMode": when_val},
                            "Entries": bi_entries
                        })
                    continue

                bi_fields = {}

                all_keys = set(lang1_data.keys()) | set(lang2_data.keys())
                for key in all_keys:
                    item1 = lang1_data.get(key, {})
                    item2 = lang2_data.get(key, {})

                    dn1 = item1.get("displayName", "") if isinstance(item1, dict) else item1
                    desc1 = item1.get("description", "") if isinstance(item1, dict) else ""
                    dn2 = item2.get("displayName", "") if isinstance(item2, dict) else item2
                    desc2 = item2.get("description", "") if isinstance(item2, dict) else ""

                    if not dn1 and not desc1:
                        if dn2:
                            bi_field_values = {}
                            if dn_field is not None:
                                bi_field_values[str(dn_field)] = f" / {dn2}"
                            if desc_field is not None and desc2:
                                bi_field_values[str(desc_field)] = f" / {desc2}"
                            bi_fields[key] = bi_field_values
                        continue

                    bi_field_values = {}
                    if dn1 and dn2:
                        bi_field_values[str(dn_field)] = sep.format(left=dn1, right=dn2)
                    elif dn1:
                        bi_field_values[str(dn_field)] = dn1
                    elif dn2:
                        bi_field_values[str(dn_field)] = f" / {dn2}"

                    if desc1 and desc2:
                        bi_field_values[str(desc_field)] = sep.format(left=desc1, right=desc2)
                    elif desc1:
                        bi_field_values[str(desc_field)] = desc1
                    elif desc2:
                        bi_field_values[str(desc_field)] = f" / {desc2}"
                    bi_fields[key] = bi_field_values

                if bi_fields:
                    content_changes.append({
                        "Action": "EditData",
                        "Target": asset_path,
                        "When": {"BilingualMode": when_val},
                        "Fields": bi_fields
                    })

    # Add font redirect patches for cross-CJK pairs (ja:zh, zh:ja, ko:zh, etc.)
    cjk_pairs = {"ja:zh", "zh:ja", "ko:zh", "zh:ko", "ja:ko", "ko:ja"}
    for pair in args.pairs:
        if pair in cjk_pairs:
            pair_code = pair.replace(':', '-')
            for font_name in ["SpriteFont1", "SmallFont"]:
                from_file = f"assets/{font_name}.zh-CN.xnb"
                if (OUTPUT_DIR / from_file).exists():
                    content_changes.append({
                        "Action": "Load",
                        "Target": f"Fonts/{font_name}",
                        "FromFile": from_file,
                        "When": {"BilingualMode": pair_code}
                    })
                    print(f"  字体重定向: {font_name} -> {from_file} (when={pair_code})")

    allow_values = "off, " + ", ".join(all_pair_codes)

    content_json = {
        "Format": "2.0.0",
        "ConfigSchema": {
            "BilingualMode": {
                "AllowValues": allow_values,
                "Default": all_pair_codes[0]
            }
        },
        "Changes": content_changes
    }

    # 确保输出目录存在（CI 中 gitignored 目录不存在）
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(OUTPUT_DIR / "content.json", 'w', encoding='utf-8') as f:
        json.dump(content_json, f, indent=2, ensure_ascii=False)

    script_dir = Path(__file__).parent
    for f in ["manifest.json", "config.json"]:
        src = script_dir / ".." / "BilingualMod" / f
        if src.exists():
            shutil.copy2(str(src), str(OUTPUT_DIR / f))
            print(f"已复制 {f}")

    patch_count = len(content_changes)
    print(f"处理完成：补丁数 {patch_count}")
    print(f"语言对：{', '.join(f'{pair}' for pair in args.pairs)}")
    print(f"Content Patcher 包已生成至：{OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
