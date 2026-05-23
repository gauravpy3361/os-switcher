#!/usr/bin/env python3
"""Build script for Windows Inno Setup installer."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_iscc() -> Path | None:
    # 1. Search in PATH
    iscc_bin = shutil.which("ISCC.exe") or shutil.which("iscc")
    if iscc_bin:
        return Path(iscc_bin)

    # 2. Check standard installation folders
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    local_app_data = Path(os.environ.get("LocalAppData", os.path.expandvars(r"%USERPROFILE%\AppData\Local")))

    candidates = [
        program_files_x86 / "Inno Setup 6" / "ISCC.exe",
        program_files_x86 / "Inno Setup 5" / "ISCC.exe",
        program_files / "Inno Setup 6" / "ISCC.exe",
        program_files / "Inno Setup 5" / "ISCC.exe",
        local_app_data / "Programs" / "Inno Setup 6" / "ISCC.exe",
        local_app_data / "Programs" / "Inno Setup 5" / "ISCC.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def main() -> int:
    if sys.platform != "win32":
        print(f"Error: Installer can only be compiled on Windows. Current platform: {sys.platform}", file=sys.stderr)
        return 1

    iscc_path = find_iscc()
    if not iscc_path:
        print("Error: Inno Setup compiler (ISCC.exe) not found.", file=sys.stderr)
        print("Please install Inno Setup 6 from https://jrsoftware.org/isdl.php and try again.", file=sys.stderr)
        return 1

    print(f"Found Inno Setup Compiler: {iscc_path}")

    iss_path = ROOT / "windows" / "OSSwitcher-Setup.iss"
    if not iss_path.exists():
        print(f"Error: Inno Setup script not found at {iss_path}", file=sys.stderr)
        return 1

    dist_dir = ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    print(f"Compiling Inno Setup script: {iss_path}")
    print(f"Output directory: {dist_dir}")

    try:
        subprocess.run(
            [str(iscc_path), f"/O{dist_dir}", str(iss_path)],
            check=True,
            text=True,
        )
        print("\nInstaller built successfully!")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"\nError: ISCC compiler failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode
    except Exception as exc:
        print(f"\nError: Failed to execute Inno Setup compiler: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
