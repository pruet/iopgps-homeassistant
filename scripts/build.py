#!/usr/bin/env python3
"""Build script for IOPGPS Home Assistant integration release packages."""
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "custom_components" / "iopgps"
DIST_DIR = ROOT / "dist"

EXCLUDE_DIRS = {"tests", "__pycache__"}
EXCLUDE_EXTS = {".pyc", ".pyo", ".DS_Store"}


def main():
    with open(SRC_DIR / "manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    version = manifest.get("version", "unknown")
    domain = manifest.get("domain", "iopgps")

    DIST_DIR.mkdir(exist_ok=True)
    zip_path = DIST_DIR / f"{domain}.zip"
    versioned_zip_path = DIST_DIR / f"{domain}-v{version}.zip"

    files_to_pack = []
    for file_path in sorted(SRC_DIR.rglob("*")):
        if file_path.is_dir():
            continue
        rel_to_src = file_path.relative_to(SRC_DIR)
        parts = rel_to_src.parts
        if any(part in EXCLUDE_DIRS for part in parts):
            continue
        if file_path.suffix in EXCLUDE_EXTS:
            continue
        # In the archive, structure as domain/... so extracting into custom_components/ creates custom_components/<domain>/
        archive_name = Path(domain) / rel_to_src
        files_to_pack.append((file_path, archive_name))

    print(f"Building installable package for {domain} v{version}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, archive_name in files_to_pack:
            print(f"  + {archive_name}")
            zf.write(file_path, str(archive_name))

    shutil.copyfile(zip_path, versioned_zip_path)

    print(f"\nCreated packages successfully:")
    print(f"  - {zip_path} ({zip_path.stat().st_size} bytes)")
    print(f"  - {versioned_zip_path} ({versioned_zip_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
