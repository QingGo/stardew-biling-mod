import json
import os
import re
import shutil
from pathlib import Path

# ====== Config ======
EXPORT_DIR = Path("D:/steam/steamapps/common/Stardew Valley/Export_TextAssets")
OUTPUT_DIR = Path("./BilingualMod")
ASSETS_LIST_FILE = Path("./assets-list.txt")

BILINGUAL_TEMPLATE = "{en} / {zh}"
PIPE_BILINGUAL_TEMPLATE = "{en} | {zh}"

# 对话标记分割：#$e# (结束) 和 #$b# (换行) 是段落边界
# 在边界之间做双语拼接，避免中文被 #$e# 丢弃
DIALOGUE_SEGMENT_RE = re.compile(r'(#\$[eb]#)')
DIALOGUE_ASSET_PREFIXES = ["Characters/Dialogue/"]


def make_dialogue_bilingual(en_val: str, zh_val: str) -> str:
    """对对话条目按 #$e# / #$b# 分段后做双语，避免中文被结束标记丢弃"""
    en_parts = DIALOGUE_SEGMENT_RE.split(en_val)
    zh_parts = DIALOGUE_SEGMENT_RE.split(zh_val)

    # 如果分段结构不一致（中英标记数量不同），回退到简单拼接
    if len(en_parts) != len(zh_parts):
        return BILINGUAL_TEMPLATE.format(en=en_val, zh=zh_val)

    result = []
    for en_part, zh_part in zip(en_parts, zh_parts):
        if en_part in ('#$e#', '#$b#'):
            result.append(en_part)
        else:
            en_text = en_part
            zh_text = zh_part
            if en_text and zh_text:
                result.append(f"{en_text} / {zh_text}")
            elif en_text:
                result.append(f"{en_text} / ")
            elif zh_text:
                result.append(f" / {zh_text}")
            else:
                result.append("")
    return "".join(result)

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


MAIL_TITLE_RE = re.compile(r'(%%?\[#\])(.*)$')
MAIL_ASSET_PATHS = ["Data/mail"]

EVENT_ASSET_PREFIX = "Data/Events/"
EVENT_TEXT_COMMANDS = ("speak ", "message ", "question ", "quickQuestion ", "textAboveHead ", "dialogue ")


def split_event_script(script: str) -> list:
    """按 / 分割事件脚本，但尊重引号内的内容"""
    parts = []
    current = []
    in_quotes = False
    for c in script:
        if c == '"':
            in_quotes = not in_quotes
            current.append(c)
        elif c == '/' and not in_quotes:
            parts.append(''.join(current))
            current = []
        else:
            current.append(c)
    if current:
        parts.append(''.join(current))
    return parts


def get_quoted_text(cmd: str) -> str:
    """从命令中提取第一个引号内的文本"""
    start = cmd.find('"')
    if start < 0:
        return ""
    end = cmd.find('"', start + 1)
    if end < 0:
        return ""
    return cmd[start + 1:end]


def replace_quoted_text(cmd: str, new_text: str) -> str:
    """替换命令中第一个引号内的文本"""
    start = cmd.find('"')
    if start < 0:
        return cmd
    end = cmd.find('"', start + 1)
    if end < 0:
        return cmd
    return cmd[:start + 1] + new_text + cmd[end:]


def is_text_command(cmd: str) -> bool:
    """判断是否为包含对话文本的命令"""
    stripped = cmd.strip()
    return any(stripped.startswith(p) for p in EVENT_TEXT_COMMANDS)


def make_event_bilingual(en_script: str, zh_script: str) -> str:
    """对事件脚本做对话双语"""
    en_parts = split_event_script(en_script)
    zh_parts = split_event_script(zh_script)

    if len(en_parts) != len(zh_parts):
        # 结构不一致，回退到简单拼接
        return BILINGUAL_TEMPLATE.format(en=en_script, zh=zh_script)

    result = []
    for en_cmd, zh_cmd in zip(en_parts, zh_parts):
        if is_text_command(en_cmd) and is_text_command(zh_cmd):
            en_text = get_quoted_text(en_cmd)
            zh_text = get_quoted_text(zh_cmd)
            if en_text and zh_text and en_text != zh_text:
                bi_text = BILINGUAL_TEMPLATE.format(en=en_text, zh=zh_text)
                result.append(replace_quoted_text(en_cmd, bi_text))
            else:
                result.append(en_cmd)
        else:
            result.append(en_cmd)

    return "/".join(result)

def make_mail_bilingual(en_val: str, zh_val: str) -> str:
    """对信件条目做双语，解决 [#] 标记重复导致正文/标题混乱的问题。

    策略：只保留 EN 的 [#] 标记和命令（%item, %money 等），
    ZH 只取纯文本部分做双语拼接。
    """
    # 提取 EN 的正文、标记、标题
    en_match = MAIL_TITLE_RE.search(en_val)
    if not en_match:
        return BILINGUAL_TEMPLATE.format(en=en_val, zh=zh_val)

    en_marker = en_match.group(1)   # "%%[#]" or "[#]"
    en_title = en_match.group(2)    # title text after marker
    en_body = en_val[:en_match.start()]

    # 提取 ZH 的正文、标题（如果有标记）
    zh_match = MAIL_TITLE_RE.search(zh_val)
    if zh_match:
        zh_body = zh_val[:zh_match.start()]
        zh_title = zh_match.group(2)
    else:
        zh_body = zh_val
        zh_title = ""

    # ZH 正文中去除 %item/%money/%quest 等命令（只取纯文本）
    # 避免命令在双语中重复执行
    zh_body_clean = re.sub(r'%[a-z]+\b.*?(?=\^|%|\[|$)', '', zh_body).strip()
    if not zh_body_clean:
        zh_body_clean = zh_body  # fallback if stripping removed everything

    body_bi = BILINGUAL_TEMPLATE.format(en=en_body, zh=zh_body_clean)
    title_bi = BILINGUAL_TEMPLATE.format(en=en_title, zh=zh_title) if zh_title else en_title
    return f"{body_bi} {en_marker}{title_bi}"


def is_string_asset(asset_path: str) -> bool:
    """判断是否为纯文本 Dict<string,string> 资产"""
    return any(asset_path.startswith(p) for p in STRING_ASSET_PREFIXES) or asset_path in [
        "Data/ExtraDialogue", "Data/mail",
        "Data/TV/CookingChannel", "Data/TV/TipChannel"
    ] or asset_path.startswith(EVENT_ASSET_PREFIX)


def is_data_asset(asset_path: str) -> bool:
    """判断是否为 Data/* 结构化资产"""
    return asset_path in DATA_FIELD_MAP


def main():
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
            print(f"警告：缺失英文资产 {asset_path}，跳过")
            continue

        if is_string_asset(asset_path):
            # ====== 字符串资产：生成两套 EditData + Entries 补丁 ======
            # 中文模式：0 补丁（通过 When 条件跳过，游戏原生 .zh-CN 覆盖层提供中文）
            # English 模式：EditData + Entries 覆盖 .zh-CN 覆盖层为英文
            # Bilingual 模式：EditData + Entries 覆盖 .zh-CN 覆盖层为双语
            if not zh_file.exists():
                print(f"警告：缺失中文资产 {asset_path}，将使用英文代替")
                zh_data = None
            else:
                zh_data = load_json(zh_file)

            en_data = load_json(en_file)

            all_keys = set(en_data.keys())
            if zh_data:
                all_keys |= set(zh_data.keys())

            is_dialogue = any(asset_path.startswith(p) for p in DIALOGUE_ASSET_PREFIXES)
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
                        bilingual_data[key] = BILINGUAL_TEMPLATE.format(en=en_val, zh=zh_val)
                    elif en_val:
                        bilingual_data[key] = f"{en_val} / "
                    elif zh_val:
                        bilingual_data[key] = f" / {zh_val}"
                    else:
                        bilingual_data[key] = ""

            # English 模式补丁（仅包含英文有的键；中文独有键保持覆盖层原样）
            content_changes.append({
                "Action": "EditData",
                "Target": asset_path,
                "When": { "LanguageMode": "English" },
                "Entries": dict(en_data)
            })
            # Bilingual 模式补丁（包含所有键的并集）
            content_changes.append({
                "Action": "EditData",
                "Target": asset_path,
                "When": { "LanguageMode": "Bilingual" },
                "Entries": bilingual_data
            })
            string_count += 1

        elif is_data_asset(asset_path):
            # ====== Data 资产：生成 EditData Fields 补丁 ======
            if not zh_file.exists():
                print(f"警告：缺失中文 Data 资产 {asset_path}，跳过")
                continue

            en_data = load_json(en_file)
            zh_data = load_json(zh_file)

            field_map = DATA_FIELD_MAP[asset_path]
            asset_type = field_map["type"]
            dn_field = field_map["displayName"]
            desc_field = field_map["description"]
            sep = PIPE_BILINGUAL_TEMPLATE if asset_type == "pipe" else BILINGUAL_TEMPLATE

            if asset_type == "caret":
                # ====== ^ 分隔型：EditData + Entries 全值替换 ======
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

                    # English 模式：用 EN 原始值
                    if en_raw:
                        en_entries[key] = en_raw

                    # Bilingual 模式：替换相关字段为双语
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

                # 生成 English 补丁
                if en_entries:
                    content_changes.append({
                        "Action": "EditData",
                        "Target": asset_path,
                        "When": {"LanguageMode": "English"},
                        "Entries": en_entries
                    })
                # 生成 Bilingual 补丁
                if bi_entries:
                    content_changes.append({
                        "Action": "EditData",
                        "Target": asset_path,
                        "When": {"LanguageMode": "Bilingual"},
                        "Entries": bi_entries
                    })
                data_count += 1
                continue

            # 构建 English 模式的 Fields 补丁
            en_fields = {}
            # 构建 Bilingual 模式的 Fields 补丁
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
                    # 只有中文的键，在 English 模式保持中文，Bilingual 模式显示 " / 中文"
                    if zh_dn:
                        bi_field_values = {}
                        if dn_field is not None:
                            bi_field_values[str(dn_field)] = f" / {zh_dn}"
                        if desc_field is not None and zh_desc:
                            bi_field_values[str(desc_field)] = f" / {zh_desc}"
                        bi_fields[key] = bi_field_values
                    continue

                # English 模式：恢复为纯英文
                en_field_values = {}
                if en_dn:
                    en_field_values[str(dn_field)] = en_dn
                if en_desc:
                    en_field_values[str(desc_field)] = en_desc
                en_fields[key] = en_field_values

                # Bilingual 模式：中英双语
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

            data_count += 1

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

    print(f"处理完成：字符串资产 {string_count} 个（EditData），Data 资产 {data_count} 个（EditData Fields）")
    print(f"Content Patcher 包已生成至：{OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
