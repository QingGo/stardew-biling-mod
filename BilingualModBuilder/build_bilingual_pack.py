import json
import os
import shutil
from pathlib import Path

# ====== Config ======
EXPORT_DIR = Path("D:/steam/steamapps/common/Stardew Valley/Export_TextAssets")
OUTPUT_DIR = Path("./BilingualMod")
ASSETS_LIST_FILE = Path("./assets-list.txt")

BILINGUAL_TEMPLATE = "{en} / {zh}"
PIPE_BILINGUAL_TEMPLATE = "{en} | {zh}"

# Data/* 资产的字段映射 (管道分隔型使用索引，模型型使用命名字段)
DATA_FIELD_MAP = {
    # 模型型 (named fields)
    "Data/Objects":   { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/Tools":     { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/Weapons":   { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/Shirts":    { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/Pants":     { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/BigCraftables": { "type": "model", "displayName": "DisplayName", "description": "Description" },
    "Data/Powers":    { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    "Data/Trinkets":  { "type": "model",  "displayName": "DisplayName", "description": "Description" },
    # 管道分隔型 (numeric index)
    "Data/hats":      { "type": "pipe",   "displayName": 5, "description": 1 },
    "Data/Boots":     { "type": "pipe",   "displayName": 6, "description": 1 },
    "Data/Quests":    { "type": "pipe",   "displayName": 1, "description": 2 },
    "Data/SecretNotes":  { "type": "pipe",   "displayName": 0, "description": 1 },
    "Data/EngagementDialogue": { "type": "pipe", "displayName": 0, "description": 1 },
}

# 只处理 Load 的资产类型前缀 (不生成 EditData)
STRING_ASSET_PREFIXES = ["Strings/", "Characters/Dialogue/"]


def asset_path_to_filename(asset_path: str) -> str:
    return asset_path.replace("/", "_").replace("\\", "_") + ".json"


def load_json(file_path: Path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data, file_path: Path):
    os.makedirs(file_path.parent, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_string_asset(asset_path: str) -> bool:
    """判断是否为纯文本 Dict<string,string> 资产"""
    return any(asset_path.startswith(p) for p in STRING_ASSET_PREFIXES) or asset_path in [
        "Data/ExtraDialogue", "Data/mail",
        "Data/TV/CookingChannel", "Data/TV/TipChannel"
    ]


def is_data_asset(asset_path: str) -> bool:
    """判断是否为 Data/* 结构化资产"""
    return asset_path in DATA_FIELD_MAP


def main():
    if not ASSETS_LIST_FILE.exists():
        print(f"错误：找不到资产列表文件 {ASSETS_LIST_FILE}")
        return

    with open(ASSETS_LIST_FILE, 'r', encoding='utf-8') as f:
        asset_paths = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # 为字符串资产准备三语目录
    langs = ["English", "Chinese", "Bilingual"]
    for lang in langs:
        (OUTPUT_DIR / "assets" / lang).mkdir(parents=True, exist_ok=True)

    content_changes = []
    load_count = 0
    edit_count = 0

    for asset_path in asset_paths:
        filename = asset_path_to_filename(asset_path)
        en_file = EXPORT_DIR / "en" / filename
        zh_file = EXPORT_DIR / "zh" / filename

        if not en_file.exists():
            print(f"警告：缺失英文资产 {asset_path}，跳过")
            continue

        if is_string_asset(asset_path):
            # ====== 字符串资产：生成三套 Load 补丁 ======
            if not zh_file.exists():
                print(f"警告：缺失中文资产 {asset_path}，将使用英文代替")
                zh_data = None
            else:
                zh_data = load_json(zh_file)

            en_data = load_json(en_file)

            save_json(en_data, OUTPUT_DIR / "assets" / "English" / filename)

            if zh_data:
                save_json(zh_data, OUTPUT_DIR / "assets" / "Chinese" / filename)
            else:
                save_json(en_data, OUTPUT_DIR / "assets" / "Chinese" / filename)

            bilingual_data = {}
            for key, en_val in en_data.items():
                zh_val = zh_data.get(key, "") if zh_data else ""
                bilingual_data[key] = BILINGUAL_TEMPLATE.format(en=en_val, zh=zh_val)
            save_json(bilingual_data, OUTPUT_DIR / "assets" / "Bilingual" / filename)

            patch = {
                "Action": "Load",
                "Target": asset_path,
                "FromFile": f"assets/{{{{LanguageMode}}}}/{filename}"
            }
            content_changes.append(patch)
            load_count += 1

        elif is_data_asset(asset_path):
            # ====== Data 资产：生成 EditData Fields 补丁 ======
            if not zh_file.exists():
                print(f"警告：缺失中文 Data 资产 {asset_path}，跳过")
                continue

            en_data = load_json(en_file)
            zh_data = load_json(zh_file)

            field_map = DATA_FIELD_MAP[asset_path]
            is_model = field_map["type"] == "model"
            dn_field = field_map["displayName"]
            desc_field = field_map["description"]

            # 构建 English 模式的 Fields 补丁
            en_fields = {}
            # 构建 Bilingual 模式的 Fields 补丁
            bi_fields = {}

            for key in en_data:
                if key not in zh_data:
                    continue

                en_item = en_data[key]
                zh_item = zh_data[key]

                en_dn = en_item.get("displayName", "")
                en_desc = en_item.get("description", "")
                zh_dn = zh_item.get("displayName", "")
                zh_desc = zh_item.get("description", "")

                if not en_dn and not en_desc:
                    continue

                # English 模式：恢复为纯英文
                en_field_values = {}
                if en_dn:
                    en_field_values[str(dn_field)] = en_dn
                if en_desc:
                    en_field_values[str(desc_field)] = en_desc
                en_fields[key] = en_field_values

                # Bilingual 模式：中英双语
                sep = PIPE_BILINGUAL_TEMPLATE if field_map["type"] == "pipe" else BILINGUAL_TEMPLATE
                bi_field_values = {}
                if en_dn and zh_dn:
                    bi_field_values[str(dn_field)] = sep.format(en=en_dn, zh=zh_dn)
                elif en_dn:
                    bi_field_values[str(dn_field)] = en_dn

                if en_desc and zh_desc:
                    bi_field_values[str(desc_field)] = sep.format(en=en_desc, zh=zh_desc)
                elif en_desc:
                    bi_field_values[str(desc_field)] = en_desc
                bi_fields[key] = bi_field_values

            # 生成 English 补丁
            if en_fields:
                content_changes.append({
                    "Action": "EditData",
                    "Target": asset_path,
                    "When": { "LanguageMode": "English" },
                    "Fields": en_fields
                })

            # 生成 Bilingual 补丁
            if bi_fields:
                content_changes.append({
                    "Action": "EditData",
                    "Target": asset_path,
                    "When": { "LanguageMode": "Bilingual" },
                    "Fields": bi_fields
                })

            edit_count += 1

        else:
            print(f"警告：未知资产类型 {asset_path}，跳过")

    content_json = {
        "Format": "2.0.0",
        "ConfigSchema": {
            "LanguageMode": {
                "AllowValues": "English, Chinese, Bilingual",
                "Default": "Chinese"
            }
        },
        "Changes": content_changes
    }

    with open(OUTPUT_DIR / "content.json", 'w', encoding='utf-8') as f:
        json.dump(content_json, f, indent=2, ensure_ascii=False)

    # 复制 manifest.json 和 config.json
    script_dir = Path(__file__).parent
    for f in ["manifest.json", "config.json"]:
        src = script_dir / ".." / "BilingualMod" / f
        if src.exists():
            shutil.copy2(str(src), str(OUTPUT_DIR / f))
            print(f"已复制 {f}")

    print(f"处理完成：Load 资产 {load_count} 个，EditData 资产 {edit_count} 个")
    print(f"Content Patcher 包已生成至：{OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
