#!/usr/bin/env python3
"""Create a public release zip without local machine config."""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCLUDES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "dist",
}
EXCLUDED_FILES = {
    "config.json",
}


def read_version() -> str:
    version_path = ROOT / "VERSION"
    return version_path.read_text(encoding="utf-8").strip()


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in DEFAULT_EXCLUDES for part in relative.parts):
        return False
    if relative.name in EXCLUDED_FILES:
        return False
    if relative.suffix in {".pyc", ".pyo"}:
        return False
    return path.is_file()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()

    version = read_version()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = args.output_dir / f"os-switcher-{version}.zip"

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if should_include(path):
                archive.write(path, path.relative_to(ROOT))

    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
