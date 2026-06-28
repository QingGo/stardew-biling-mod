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

PIPE_BILINGUAL_TEMPLATE = "{en} | {zh}"

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
    args = parser.parse_args()

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
    string_count = 0
    data_count = 0

    for asset_path in asset_paths:
        filename = asset_path_to_filename(asset_path)
        en_file = EXPORT_DIR / "en" / filename
        zh_file = EXPORT_DIR / "zh" / filename

        if not en_file.exists():
            print(f"警告：缺失英文资产 {asset_path}（查找路径：{en_file}），跳过")
            continue

        if is_festival_asset(asset_path):
            if not zh_file.exists():
                print(f"警告：缺失中文节日资产 {asset_path}，跳过")
                continue
            en_data = load_json(en_file)
            zh_data = load_json(zh_file)
            en_name = en_data.get("name", "")
            zh_name = zh_data.get("name", "")
            if not en_name:
                print(f"警告：节日 {asset_path} 缺少 name 字段，跳过")
                continue

            entries = {}
            entries["name"] = f"{en_name} / {zh_name}" if zh_name else en_name

            for key in en_data:
                if key == "name":
                    continue
                en_val = en_data.get(key, "")
                zh_val = zh_data.get(key, "")
                if not en_val or en_val == zh_val:
                    continue  # data-only key (conditions etc.), skip
                if "/" in en_val and any(cmd in en_val for cmd in FESTIVAL_CMD_PATTERNS):
                    entries[key] = make_event_bilingual(en_val, zh_val)
                else:
                    entries[key] = make_dialogue_bilingual(en_val, zh_val)

            content_changes.append({
                "Action": "EditData",
                "Target": asset_path,
                "When": {"BilingualMode": "true"},
                "Entries": entries
            })
            data_count += 1

        elif is_string_asset(asset_path):
            if not zh_file.exists():
                print(f"警告：缺失中文资产 {asset_path}，将使用英文代替")
                zh_data = None
            else:
                zh_data = load_json(zh_file)

            en_data = load_json(en_file)

            all_keys = set(en_data.keys())
            if zh_data:
                all_keys |= set(zh_data.keys())

            is_dialogue = (
                any(asset_path.startswith(p) for p in DIALOGUE_ASSET_PREFIXES)
                or asset_path == "Data/ExtraDialogue"
                or asset_path == "Strings/MovieReactions"
                or asset_path == "Strings/SpecialOrderStrings"
            )
            is_mail = asset_path in MAIL_ASSET_PATHS
            is_event = asset_path.startswith(EVENT_ASSET_PREFIX)

            bilingual_data = {}
            for key in all_keys:
                en_val = en_data.get(key, "")
                zh_val = zh_data.get(key, "") if zh_data else ""

                if is_mail:
                    bilingual_data[key] = make_mail_bilingual(en_val, zh_val)
                elif is_event:
                    bilingual_data[key] = make_event_bilingual(en_val, zh_val)
                elif is_dialogue:
                    bilingual_data[key] = make_dialogue_bilingual(en_val, zh_val)
                else:
                    if en_val and zh_val:
                        if '$q' in en_val and '$q' in zh_val:
                            bilingual_data[key] = bilingualize_event_quoted_text(en_val, zh_val)
                        else:
                            bilingual_data[key] = bilingualize_pair(en_val, zh_val)
                    elif en_val:
                        bilingual_data[key] = f"{en_val} / "
                    elif zh_val:
                        bilingual_data[key] = f" / {zh_val}"
                    else:
                        bilingual_data[key] = ""

            content_changes.append({
                "Action": "EditData",
                "Target": asset_path,
                "When": { "BilingualMode": "true" },
                "Entries": bilingual_data
            })
            string_count += 1

        elif is_data_asset(asset_path):
            if not zh_file.exists():
                print(f"警告：缺失中文 Data 资产 {asset_path}，跳过")
                continue

            en_data = load_json(en_file)
            zh_data = load_json(zh_file)

            field_map = DATA_FIELD_MAP[asset_path]
            asset_type = field_map["type"]

            if asset_type == "pipe_multi":
                delimiter = field_map.get("delimiter", "/")
                text_fields = field_map["textFields"]
                bi_sep = PIPE_BILINGUAL_TEMPLATE
                bi_fields_data = {}

                all_keys = set(en_data.keys()) | set(zh_data.keys())
                for key in all_keys:
                    en_item = en_data.get(key, {})
                    zh_item = zh_data.get(key, {})

                    en_raw = en_item.get("_raw", "") if isinstance(en_item, dict) else ""
                    zh_raw = zh_item.get("_raw", "") if isinstance(zh_item, dict) else ""

                    if not en_raw or not zh_raw:
                        en_dn = en_item.get("displayName", "") if isinstance(en_item, dict) else ""
                        zh_dn = zh_item.get("displayName", "") if isinstance(zh_item, dict) else ""
                        if en_dn and zh_dn:
                            bi_fields_data[key] = {str(text_fields[0]): bi_sep.format(en=en_dn, zh=zh_dn)}
                        continue

                    en_fields_raw = en_raw.split(delimiter)
                    zh_fields_raw = zh_raw.split(delimiter)

                    field_vals = {}
                    for idx in text_fields:
                        en_f = en_fields_raw[idx] if idx < len(en_fields_raw) else ""
                        zh_f = zh_fields_raw[idx] if idx < len(zh_fields_raw) else ""
                        if en_f and zh_f:
                            field_vals[str(idx)] = bi_sep.format(en=en_f, zh=zh_f)
                        elif en_f:
                            field_vals[str(idx)] = f"{en_f} | "
                        elif zh_f:
                            field_vals[str(idx)] = f" | {zh_f}"
                    if field_vals:
                        bi_fields_data[key] = field_vals

                if bi_fields_data:
                    content_changes.append({
                        "Action": "EditData",
                        "Target": asset_path,
                        "When": { "BilingualMode": "true" },
                        "Fields": bi_fields_data
                    })
                data_count += 1
                continue

            dn_field = field_map["displayName"]
            desc_field = field_map["description"]
            sep = PIPE_BILINGUAL_TEMPLATE if asset_type == "pipe" else BILINGUAL_TEMPLATE

            if asset_type == "caret":
                delimiter = field_map.get("delimiter", "^")
                en_entries = {}
                bi_entries = {}

                all_keys = set(en_data.keys()) | set(zh_data.keys())
                for key in all_keys:
                    en_item = en_data.get(key, {})
                    zh_item = zh_data.get(key, {})

                    if not isinstance(en_item, dict):
                        en_item = {"_raw": str(en_item), "displayName": str(en_item), "description": ""}
                    if not isinstance(zh_item, dict):
                        zh_item = {"_raw": str(zh_item), "displayName": str(zh_item), "description": ""}

                    en_raw = en_item.get("_raw", "")
                    zh_raw = zh_item.get("_raw", "")

                    if not en_raw and not zh_raw:
                        continue

                    if en_raw:
                        en_entries[key] = en_raw

                    if en_raw or zh_raw:
                        en_fields = en_raw.split(delimiter) if en_raw else []
                        zh_fields = zh_raw.split(delimiter) if zh_raw else []
                        max_len = max(len(en_fields), len(zh_fields))
                        bi_fields = [""] * max_len
                        for i in range(max_len):
                            en_f = en_fields[i] if i < len(en_fields) else ""
                            zh_f = zh_fields[i] if i < len(zh_fields) else ""
                            if i in (dn_field, desc_field) and en_f and zh_f:
                                bi_fields[i] = f"{en_f} / {zh_f}"
                            elif i in (dn_field, desc_field) and en_f and not zh_f:
                                bi_fields[i] = f"{en_f} / "
                            elif i in (dn_field, desc_field) and not en_f and zh_f:
                                bi_fields[i] = f" / {zh_f}"
                            else:
                                if en_f and zh_f and en_f != zh_f:
                                    bi_fields[i] = f"{en_f} / {zh_f}"
                                else:
                                    bi_fields[i] = en_f or zh_f
                        bi_entries[key] = delimiter.join(bi_fields)

                if bi_entries:
                    content_changes.append({
                        "Action": "EditData",
                        "Target": asset_path,
                        "When": {"BilingualMode": "true"},
                        "Entries": bi_entries
                    })
                data_count += 1
                continue

            en_fields = {}
            bi_fields = {}

            all_keys = set(en_data.keys()) | set(zh_data.keys())
            for key in all_keys:
                en_item = en_data.get(key, {})
                zh_item = zh_data.get(key, {})

                en_dn = en_item.get("displayName", "") if isinstance(en_item, dict) else en_item
                en_desc = en_item.get("description", "") if isinstance(en_item, dict) else ""
                zh_dn = zh_item.get("displayName", "") if isinstance(zh_item, dict) else zh_item
                zh_desc = zh_item.get("description", "") if isinstance(zh_item, dict) else ""

                if not en_dn and not en_desc:
                    if zh_dn:
                        bi_field_values = {}
                        if dn_field is not None:
                            bi_field_values[str(dn_field)] = f" / {zh_dn}"
                        if desc_field is not None and zh_desc:
                            bi_field_values[str(desc_field)] = f" / {zh_desc}"
                        bi_fields[key] = bi_field_values
                    continue

                en_field_values = {}
                if en_dn:
                    en_field_values[str(dn_field)] = en_dn
                if en_desc:
                    en_field_values[str(desc_field)] = en_desc
                en_fields[key] = en_field_values

                bi_field_values = {}
                if en_dn and zh_dn:
                    bi_field_values[str(dn_field)] = sep.format(en=en_dn, zh=zh_dn)
                elif en_dn:
                    bi_field_values[str(dn_field)] = en_dn
                elif zh_dn:
                    bi_field_values[str(dn_field)] = f" / {zh_dn}"

                if en_desc and zh_desc:
                    bi_field_values[str(desc_field)] = sep.format(en=en_desc, zh=zh_desc)
                elif en_desc:
                    bi_field_values[str(desc_field)] = en_desc
                elif zh_desc:
                    bi_field_values[str(desc_field)] = f" / {zh_desc}"
                bi_fields[key] = bi_field_values

            if bi_fields:
                content_changes.append({
                    "Action": "EditData",
                    "Target": asset_path,
                    "When": { "BilingualMode": "true" },
                    "Fields": bi_fields
                })
            data_count += 1

        else:
            print(f"警告：未知资产类型 {asset_path}，跳过")

    content_json = {
        "Format": "2.0.0",
        "ConfigSchema": {
            "BilingualMode": {
                "AllowValues": "true, false",
                "Default": "true"
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

    print(f"处理完成：字符串资产 {string_count} 个（EditData），Data 资产 {data_count} 个（EditData Fields）")
    print(f"Content Patcher 包已生成至：{OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
