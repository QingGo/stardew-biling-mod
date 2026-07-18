"""
Config builder: assembles the content.json payload + manifest sync.
"""
import json
import os
import shutil
from pathlib import Path


def build_content_json(content_changes, all_pair_codes):
    """Assemble the top-level content.json object for Content Patcher v2.0.0."""
    allow_values = "off, " + ", ".join(all_pair_codes)
    return {
        "Format": "2.0.0",
        "ConfigSchema": {
            "BilingualMode": {
                "AllowValues": allow_values,
                "Default": all_pair_codes[0] if all_pair_codes else "off",
            }
        },
        "Changes": content_changes,
    }


def write_content_pack(content_json, output_dir: Path, root_bilingual_dir: Path):
    """Write content.json to output_dir, copy manifest/config, sync root for tests."""
    os.makedirs(output_dir, exist_ok=True)

    out_path = output_dir / "content.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(content_json, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out_path}")

    # Copy manifest.json and config.json from root BilingualMod/ (source of truth)
    for name in ("manifest.json", "config.json"):
        src = root_bilingual_dir / name
        if src.exists():
            shutil.copy2(str(src), str(output_dir / name))
            print(f"Copied {name}")

    # Also sync generated content.json back to root BilingualMod/ for tests
    shutil.copy2(str(out_path), str(root_bilingual_dir / "content.json"))
    print(f"Synced content.json to {root_bilingual_dir}")