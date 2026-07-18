"""
Build a ready-to-use release zip of BilingualMod for end users.

The zip includes everything the player needs:
  - manifest.json
  - content.json (generated)
  - config.json (default BilingualMode)
  - assets/  (merged fonts + any other content assets)

Usage:
    python make_release.py                 # uses ../BilingualMod as source
    python make_release.py --output out.zip
"""
import argparse
import datetime
import json
import os
import sys
import shutil
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
SOURCE_DIR = SCRIPT_DIR.parent / 'BilingualMod'


def get_version() -> str:
    manifest = SOURCE_DIR / 'manifest.json'
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding='utf-8'))
        return data.get('Version', '0.0.0')
    return '0.0.0'


def collect_files() -> list:
    """Return list of (source_path, archive_path) tuples to include."""
    if not SOURCE_DIR.exists():
        print(f'Error: source dir not found: {SOURCE_DIR}', file=sys.stderr)
        sys.exit(1)

    files = []
    for root, dirs, names in os.walk(SOURCE_DIR):
        for name in names:
            full = Path(root) / name
            rel = full.relative_to(SOURCE_DIR)
            archive_path = Path('BilingualMod') / rel
            files.append((full, archive_path))
    return files


def make_zip(output_path: Path) -> None:
    files = collect_files()
    if not files:
        print('Error: no files found to package', file=sys.stderr)
        sys.exit(1)

    print(f'Source: {SOURCE_DIR}')
    print(f'Output: {output_path}')
    print(f'Files:  {len(files)}')

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for src, arc in files:
            zf.write(src, str(arc).replace('\\', '/'))
            print(f'  + {arc}')

    print(f'\nCreated release archive: {output_path}')
    print(f'  Size: {output_path.stat().st_size:,} bytes')


def main():
    parser = argparse.ArgumentParser(description='Package BilingualMod for release')
    parser.add_argument('--output', '-o', type=Path, default=None,
                        help='Output zip path (default: auto-named with version + date)')
    args = parser.parse_args()

    version = get_version()
    if args.output is None:
        timestamp = datetime.datetime.now().strftime('%Y%m%d')
        args.output = SCRIPT_DIR / f'BilingualMod-v{version}-{timestamp}.zip'
    else:
        args.output = Path(args.output)

    make_zip(args.output)


if __name__ == '__main__':
    main()