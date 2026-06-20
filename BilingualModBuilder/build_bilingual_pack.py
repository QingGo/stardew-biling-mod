import json
import os
import shutil
from pathlib import Path

# ====== Config ======
EXPORT_DIR = Path("D:/steam/steamapps/common/Stardew Valley/Export_TextAssets")
OUTPUT_DIR = Path("./BilingualMod")
ASSETS_LIST_FILE = Path("./assets-list.txt")

BILINGUAL_TEMPLATE = "{en} / {zh}"


def asset_path_to_filename(asset_path: str) -> str:
    return asset_path.replace("/", "_").replace("\\", "_") + ".json"


def load_json(file_path: Path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data, file_path: Path):
    os.makedirs(file_path.parent, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    if not ASSETS_LIST_FILE.exists():
        print(f"错误：找不到资产列表文件 {ASSETS_LIST_FILE}")
        return

    with open(ASSETS_LIST_FILE, 'r', encoding='utf-8') as f:
        asset_paths = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    langs = ["English", "Chinese", "Bilingual"]
    for lang in langs:
        (OUTPUT_DIR / "assets" / lang).mkdir(parents=True, exist_ok=True)

    content_patches = []

    for asset_path in asset_paths:
        filename = asset_path_to_filename(asset_path)

        en_file = EXPORT_DIR / "en" / filename
        zh_file = EXPORT_DIR / "zh" / filename

        if not en_file.exists():
            print(f"警告：缺失英文资产 {asset_path}，跳过")
            continue

        if not zh_file.exists():
            print(f"警告：缺失中文资产 {asset_path}，将使用英文代替中文部分")
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
            zh_val = ""
            if zh_data and key in zh_data:
                zh_val = zh_data[key]
            else:
                zh_val = ""
            bilingual_data[key] = BILINGUAL_TEMPLATE.format(en=en_val, zh=zh_val)
        save_json(bilingual_data, OUTPUT_DIR / "assets" / "Bilingual" / filename)

        from_file = f"assets/{{{{LanguageMode}}}}/{filename}"
        patch = {
            "Action": "Load",
            "Target": asset_path,
            "FromFile": from_file
        }
        content_patches.append(patch)

    content_json = {
        "Format": "2.0.0",
        "ConfigSchema": {
            "LanguageMode": {
                "AllowValues": "English, Chinese, Bilingual",
                "Default": "Chinese"
            }
        },
        "Changes": content_patches
    }
    with open(OUTPUT_DIR / "content.json", 'w', encoding='utf-8') as f:
        json.dump(content_json, f, indent=2, ensure_ascii=False)

    # 复制 manifest.json 和 config.json 模板
    script_dir = Path(__file__).parent
    for f in ["manifest.json", "config.json"]:
        src = script_dir / ".." / "BilingualMod" / f
        if src.exists():
            shutil.copy2(str(src), str(OUTPUT_DIR / f))
            print(f"已复制 {f}")

    print(f"处理完成，共处理 {len(content_patches)} 个资产。")
    print(f"Content Patcher 包已生成至：{OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
