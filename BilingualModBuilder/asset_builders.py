"""
Asset builders: convert source-language data into bilingual CP patches.

Each builder takes the asset path, two language data dicts, and a When
condition value, and returns a single CP "Changes" entry (or None if the
asset produces no bilingual diffs).
"""
from pathlib import Path

from parsers import (
    BILINGUAL_TEMPLATE,
    PIPE_BILINGUAL_TEMPLATE,
    bilingualize_pair,
    bilingualize_event_quoted_text,
    make_dialogue_bilingual,
    make_mail_bilingual,
    make_event_bilingual,
)

# ====== Constants shared between builders ======
FESTIVAL_CMD_PATTERNS = ("speak ", "pause ", "move ", "jump ", "warp ")

# Dialogue detection includes prefixes plus extra dialogue-like string assets.
DIALOGUE_ASSET_PREFIXES = ["Characters/Dialogue/"]
DIALOGUE_EXTRA_ASSETS = {
    "Data/ExtraDialogue",
    "Strings/MovieReactions",
    "Strings/SpecialOrderStrings",
    "Strings/StringsFromCSFiles",
    "Strings/1_6_Strings",
    "Strings/StringsFromMaps",
    "Strings/SimpleNonVillagerDialogues",
}
MAIL_ASSET_PATHS = {"Data/mail"}
EVENT_ASSET_PREFIX = "Data/Events/"
COOKING_ASSET_PATH = "Data/TV/CookingChannel"

# Data/* structured asset field maps
DATA_FIELD_MAP = {
    "Data/Objects":          {"type": "model", "displayName": "DisplayName", "description": "Description"},
    "Data/Tools":            {"type": "model", "displayName": "DisplayName", "description": "Description"},
    "Data/Weapons":          {"type": "model", "displayName": "DisplayName", "description": "Description"},
    "Data/Shirts":           {"type": "model", "displayName": "DisplayName", "description": "Description"},
    "Data/Pants":            {"type": "model", "displayName": "DisplayName", "description": "Description"},
    "Data/BigCraftables":    {"type": "model", "displayName": "DisplayName", "description": "Description"},
    "Data/Powers":           {"type": "model", "displayName": "DisplayName", "description": "Description"},
    "Data/Trinkets":         {"type": "model", "displayName": "DisplayName", "description": "Description"},
    "Data/hats":             {"type": "pipe",  "displayName": 5, "description": 1},
    "Data/Boots":            {"type": "pipe",  "displayName": 6, "description": 1},
    "Data/Quests":           {"type": "pipe",  "displayName": 1, "description": 2},
    "Data/EngagementDialogue": {"type": "pipe", "displayName": 0, "description": 1},
    "Data/SecretNotes":      {"type": "caret", "delimiter": "^", "displayName": 0, "description": 1},
    "Data/Achievements":     {"type": "caret", "delimiter": "^", "displayName": 0, "description": 1},
    "Data/Bundles":          {"type": "pipe",  "displayName": 6, "description": None},
    "Data/Monsters":         {"type": "pipe",  "displayName": 14, "description": None},
    "Data/NPCGiftTastes":    {"type": "pipe_multi", "textFields": [0, 2, 4, 6, 8], "delimiter": "/"},
}

STRING_ASSET_PREFIXES = ["Strings/", "Characters/Dialogue/"]
FESTIVAL_ASSET_PREFIX = "Data/Festivals/"


# ====== Asset type classifiers ======
def is_string_asset(asset_path: str) -> bool:
    return (
        any(asset_path.startswith(p) for p in STRING_ASSET_PREFIXES)
        or asset_path in DIALOGUE_EXTRA_ASSETS
        or asset_path in MAIL_ASSET_PATHS
        or asset_path == COOKING_ASSET_PATH
        or asset_path == "Data/TV/TipChannel"
        or asset_path == "Data/Festivals/FestivalDates"
        or asset_path.startswith(EVENT_ASSET_PREFIX)
    )


def is_data_asset(asset_path: str) -> bool:
    return asset_path in DATA_FIELD_MAP


def is_festival_asset(asset_path: str) -> bool:
    return asset_path.startswith(FESTIVAL_ASSET_PREFIX) and not asset_path.endswith("FestivalDates")


def _is_dialogue_asset(asset_path: str) -> bool:
    return (
        any(asset_path.startswith(p) for p in DIALOGUE_ASSET_PREFIXES)
        or asset_path in DIALOGUE_EXTRA_ASSETS
    )


# ====== Festival builder ======
def build_festival_patch(asset_path, lang1_data, lang2_data, when_val):
    """Build an EditData patch for festival assets (contains `name` + dialogue)."""
    name1 = lang1_data.get("name", "")
    name2 = lang2_data.get("name", "")
    if not name1:
        return None

    entries = {
        "name": BILINGUAL_TEMPLATE.format(left=name1, right=name2) if name2 else name1
    }
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

    return {
        "Action": "EditData",
        "Target": asset_path,
        "When": {"BilingualMode": when_val},
        "Entries": entries,
    }


# ====== String builder ======
def build_string_patch(asset_path, lang1_data, lang2_data, when_val):
    """Build an EditData patch for plain Dict<string,string> string assets."""
    if lang2_data is None:
        lang2_data = {}

    all_keys = set(lang1_data.keys()) | set(lang2_data.keys())

    is_dialogue = _is_dialogue_asset(asset_path)
    is_mail = asset_path in MAIL_ASSET_PATHS
    is_event = asset_path.startswith(EVENT_ASSET_PREFIX)
    is_cooking = asset_path == COOKING_ASSET_PATH

    bilingual_data = {}
    for key in all_keys:
        v1 = lang1_data.get(key, "")
        v2 = lang2_data.get(key, "")

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

    return {
        "Action": "EditData",
        "Target": asset_path,
        "When": {"BilingualMode": when_val},
        "Entries": bilingual_data,
    }


# ====== Data builder ======
def build_data_patch(asset_path, lang1_data, lang2_data, when_val):
    """Build a structured Data/* asset patch. Returns None if no diff produced."""
    field_map = DATA_FIELD_MAP[asset_path]
    asset_type = field_map["type"]

    if asset_type == "pipe_multi":
        return _build_pipe_multi_patch(asset_path, lang1_data, lang2_data, field_map, when_val)
    if asset_type == "caret":
        return _build_caret_patch(asset_path, lang1_data, lang2_data, field_map, when_val)
    return _build_model_or_pipe_patch(asset_path, lang1_data, lang2_data, field_map, when_val)


def _build_pipe_multi_patch(asset_path, l1, l2, field_map, when_val):
    delimiter = field_map.get("delimiter", "/")
    text_fields = field_map["textFields"]
    bi_sep = PIPE_BILINGUAL_TEMPLATE
    bi_fields_data = {}

    all_keys = set(l1.keys()) | set(l2.keys())
    for key in all_keys:
        item1 = l1.get(key, {})
        item2 = l2.get(key, {})

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

    if not bi_fields_data:
        return None
    return {
        "Action": "EditData",
        "Target": asset_path,
        "When": {"BilingualMode": when_val},
        "Fields": bi_fields_data,
    }


def _build_caret_patch(asset_path, l1, l2, field_map, when_val):
    delimiter = field_map.get("delimiter", "^")
    dn_field = field_map["displayName"]
    desc_field = field_map["description"]
    bi_entries = {}

    all_keys = set(l1.keys()) | set(l2.keys())
    for key in all_keys:
        item1 = l1.get(key, {})
        item2 = l2.get(key, {})

        if not isinstance(item1, dict):
            item1 = {"_raw": str(item1), "displayName": str(item1), "description": ""}
        if not isinstance(item2, dict):
            item2 = {"_raw": str(item2), "displayName": str(item2), "description": ""}

        raw1 = item1.get("_raw", "")
        raw2 = item2.get("_raw", "")
        if not raw1 and not raw2:
            continue

        fields1 = raw1.split(delimiter) if raw1 else []
        fields2 = raw2.split(delimiter) if raw2 else []
        max_len = max(len(fields1), len(fields2))

        bi_fields = [""] * max_len
        for i in range(max_len):
            f1 = fields1[i] if i < len(fields1) else ""
            f2 = fields2[i] if i < len(fields2) else ""
            text_fields = {dn_field, desc_field} - {None}
            if i in text_fields and f1 and f2:
                bi_fields[i] = f"{f1} / {f2}"
            elif i in text_fields and f1 and not f2:
                bi_fields[i] = f"{f1} / "
            elif i in text_fields and not f1 and f2:
                bi_fields[i] = f" / {f2}"
            else:
                if f1 and f2 and f1 != f2:
                    bi_fields[i] = f"{f1} / {f2}"
                else:
                    bi_fields[i] = f1 or f2
        bi_entries[key] = delimiter.join(bi_fields)

    if not bi_entries:
        return None
    return {
        "Action": "EditData",
        "Target": asset_path,
        "When": {"BilingualMode": when_val},
        "Entries": bi_entries,
    }


def _build_model_or_pipe_patch(asset_path, l1, l2, field_map, when_val):
    dn_field = field_map["displayName"]
    desc_field = field_map["description"]
    asset_type = field_map["type"]
    sep = PIPE_BILINGUAL_TEMPLATE if asset_type == "pipe" else BILINGUAL_TEMPLATE

    bi_fields = {}
    all_keys = set(l1.keys()) | set(l2.keys())
    for key in all_keys:
        item1 = l1.get(key, {})
        item2 = l2.get(key, {})

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

    if not bi_fields:
        return None
    return {
        "Action": "EditData",
        "Target": asset_path,
        "When": {"BilingualMode": when_val},
        "Fields": bi_fields,
    }


# ====== Font patches builder ======
# Pairs that need any font redirect (non-ASCII glyphs missing from active font)
# CJK-CJK pairs (ja:zh etc.) and EN-with-CJK pairs (en:zh, en:ja) need SpriteFont
# redirects because the active game font lacks those glyphs.
FONT_PATCH_PAIRS = {
    "ja:zh", "zh:ja", "ko:zh", "zh:ko", "ja:ko", "ko:ja",
    "en:zh", "en:ja", "en:ko",
}
# Pairs that also need BmFont patches. Stardew's BmFont (Fonts/Chinese,
# Fonts/Japanese) is used for loading text, TV subtitles, mail body, and
# some HUD elements. When the pair includes CJK glyphs, both BmFonts must
# be redirected to the merged versions so CJK characters render even when
# the active game language is EN (which would otherwise load a latin-only
# fallback). Korean is intentionally excluded because we don't ship
# pre-merged Korean BmFonts.
BMFONT_PAIRS = {
    "ja:zh", "zh:ja", "ko:zh", "zh:ko", "ja:ko", "ko:ja",
    "en:zh", "en:ja",
}
SPRITE_FONTS = ("SpriteFont1", "SmallFont")
BMFONTS = ("Chinese", "Japanese")


def build_font_patches(pair, pair_code, output_dir: Path):
    """Return CP Change entries that Load merged fonts when needed for this pair."""
    patches = []
    if pair not in FONT_PATCH_PAIRS:
        return patches

    # SpriteFont patch: Load the ZH-merged SpriteFont (most complete coverage)
    for font_name in SPRITE_FONTS:
        from_file = f"assets/{font_name}.zh-CN.xnb"
        if (output_dir / from_file).exists():
            patches.append({
                "Action": "Load",
                "Target": f"Fonts/{font_name}",
                "FromFile": from_file,
                "When": {"BilingualMode": pair_code},
            })

    # BmFont patches: Load merged Chinese & Japanese BmFonts for CJK pairs
    # (including en:zh/en:ja, since EN fallback lacks CJK glyphs).
    if pair in BMFONT_PAIRS:
        for bmf_name in BMFONTS:
            from_file = f"assets/{bmf_name}.xnb"
            if (output_dir / from_file).exists():
                patches.append({
                    "Action": "Load",
                    "Target": f"Fonts/{bmf_name}",
                    "FromFile": from_file,
                    "When": {"BilingualMode": pair_code},
                })
    return patches