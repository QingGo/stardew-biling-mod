"""
Build a bilingual Content Patcher pack from two-language export data.

Usage:
    python build_bilingual_pack.py --pairs en:zh de:en ja:zh

This script orchestrates per-asset builders (see asset_builders.py) to produce
the full content.json structure with one EditData/Load patch per (pair, asset).
"""
import argparse
import json
from pathlib import Path

from asset_builders import (
    build_data_patch,
    build_festival_patch,
    build_font_patches,
    build_string_patch,
    is_data_asset,
    is_festival_asset,
    is_string_asset,
)
from config_builder import build_content_json, write_content_pack

# ====== Paths & constants ======
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_EXPORT_DIR = SCRIPT_DIR.parent / "_export"
GAME_EXPORT_DIR = Path("D:/steam/steamapps/common/Stardew Valley/Export_TextAssets")
OUTPUT_DIR = Path("./BilingualMod")
ASSETS_LIST_FILE = Path("./assets-list.txt")
ROOT_BILINGUAL_DIR = SCRIPT_DIR.parent / "BilingualMod"

EXPORT_DIR = None  # set by main() via CLI arg

FONT_LIMITED_PAIRS = {"ja:zh", "zh:ja", "ko:zh", "zh:ko", "ja:ko", "ko:ja"}


def asset_path_to_filename(asset_path: str) -> str:
    return asset_path.replace("/", "_").replace("\\", "_") + ".json"


def load_json(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_export_dir(cli_arg):
    if cli_arg:
        return Path(cli_arg)
    if GAME_EXPORT_DIR.exists():
        return GAME_EXPORT_DIR
    return DEFAULT_EXPORT_DIR


def build_patch_for_asset(asset_path, lang1, lang2, when_val):
    """Dispatch a single asset to the right builder. Returns a CP change or None."""
    filename = asset_path_to_filename(asset_path)
    lang1_file = EXPORT_DIR / lang1 / filename
    lang2_file = EXPORT_DIR / lang2 / filename

    if not lang1_file.exists():
        print(f"警告：缺失 {lang1} 资产 {asset_path}（查找路径：{lang1_file}），跳过")
        return None

    if is_festival_asset(asset_path):
        if not lang2_file.exists():
            print(f"警告：缺失 {lang2} 节日资产 {asset_path}，跳过")
            return None
        return build_festival_patch(asset_path, load_json(lang1_file), load_json(lang2_file), when_val)

    if is_string_asset(asset_path):
        lang2_data = load_json(lang2_file) if lang2_file.exists() else None
        if lang2_data is None:
            print(f"警告：缺失 {lang2} 资产 {asset_path}，将使用 {lang1} 代替")
        return build_string_patch(asset_path, load_json(lang1_file), lang2_data, when_val)

    if is_data_asset(asset_path):
        if not lang2_file.exists():
            print(f"警告：缺失 {lang2} Data 资产 {asset_path}，跳过")
            return None
        return build_data_patch(asset_path, load_json(lang1_file), load_json(lang2_file), when_val)

    return None


def main():
    parser = argparse.ArgumentParser(description="Build bilingual Content Patcher pack")
    parser.add_argument("--export-dir", type=str, default=None,
                        help="Path to Export_TextAssets (default: auto-detect)")
    parser.add_argument("--pairs", type=str, nargs="+", default=["en:zh"],
                        help="Language pairs: lang1:lang2 lang1:lang2 ... (default: en:zh)")
    args = parser.parse_args()

    global EXPORT_DIR
    EXPORT_DIR = detect_export_dir(args.export_dir)

    for pair in args.pairs:
        if pair in FONT_LIMITED_PAIRS:
            print(f"注意：语言对 {pair} 需要合并字体支持（仅在 CJK 游戏语言下生效）。")
            print()
        # Warn about EN + CJK pairs which do NOT get font patches (FNA rendering bug).
        if pair.startswith("en:") and any(pair.endswith(f":{c}") for c in ("zh", "ja", "ko")):
            print(f"提示：语言对 {pair} 在 EN 游戏语言下不会加载字体补丁（已知 FNA 渲染 bug）。")
            print(f"      如需显示 CJK 字符，请将游戏语言切换为对应 CJK 语言（zh-CN/ja-JP 等）。")
            print()

    if not ASSETS_LIST_FILE.exists():
        print(f"错误：找不到资产列表文件 {ASSETS_LIST_FILE}")
        return

    with open(ASSETS_LIST_FILE, "r", encoding="utf-8") as f:
        asset_paths = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    content_changes = []
    all_pair_codes = []

    for pair in args.pairs:
        lang1, lang2 = pair.split(":")
        pair_code = f"{lang1}-{lang2}"
        all_pair_codes.append(pair_code)

        # v2.0.0: removed "true" backward-compat (CP validates ALL When values)
        for asset_path in asset_paths:
            patch = build_patch_for_asset(asset_path, lang1, lang2, pair_code)
            if patch is not None:
                content_changes.append(patch)

        # Font redirect patches (Load action) for cross-font/CJK pairs.
        # Use ROOT_BILINGUAL_DIR (which has committed assets/) rather than
        # OUTPUT_DIR (which is empty of assets until write_content_pack copies them).
        font_patches = build_font_patches(pair, pair_code, ROOT_BILINGUAL_DIR)
        for fp in font_patches:
            content_changes.append(fp)
            print(f"  Font redirect: {fp['Target']} -> {fp['FromFile']} (when={pair_code})")

    content_json = build_content_json(content_changes, all_pair_codes)
    write_content_pack(content_json, OUTPUT_DIR, ROOT_BILINGUAL_DIR)

    print(f"处理完成：补丁数 {len(content_changes)}")
    print(f"语言对：{', '.join(args.pairs)}")
    print(f"Content Patcher 包已生成至：{OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()