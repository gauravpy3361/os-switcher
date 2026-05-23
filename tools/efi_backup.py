#!/usr/bin/env python3
"""Standalone EFI backup utility for OS Switcher."""

from __future__ import annotations

import argparse
import datetime
import platform
import subprocess
import sys
from pathlib import Path

# Add current directory to path to import validate_config
sys.path.insert(0, str(Path(__file__).parent))
from validate_config import validate

ROOT = Path(__file__).resolve().parents[1]


def backup_efi_entries(backup_dir: str, os_name: str) -> str:
    path = Path(backup_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise RuntimeError(f"Failed to create backup directory '{backup_dir}': {exc}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = path / f"efi-backup-{timestamp}.txt"

    if os_name == "windows":
        cmd = ["bcdedit", "/enum", "firmware"]
    elif os_name == "linux":
        cmd = ["efibootmgr", "-v"]
    else:
        raise RuntimeError(f"Unsupported OS for EFI backup: {os_name}")

    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
        content = completed.stdout + completed.stderr
    except subprocess.SubprocessError as exc:
        raise RuntimeError(f"Command failed '{' '.join(cmd)}': {exc}")
    except Exception as exc:
        raise RuntimeError(f"Failed to run command '{' '.join(cmd)}': {exc}")

    try:
        backup_file.write_text(content, encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"Failed to write backup file '{backup_file}': {exc}")

    return str(backup_file)


def list_backups(backup_dir: str) -> list[str]:
    path = Path(backup_dir)
    if not path.exists():
        return []
    
    files = list(path.glob("efi-backup-*.txt"))
    # Sort by name (which has timestamp) descending to get newest first
    files.sort(key=lambda f: f.name, reverse=True)
    return [str(f) for f in files]


def restore_efi_backup(backup_path: str) -> None:
    path = Path(backup_path)
    if not path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"Failed to read backup file '{backup_path}': {exc}")

    print("=== EFI BACKUP CONTENTS (manual restore required) ===")
    print(content)
    print("=====================================================")
    print("Use bcdedit (Windows) or efibootmgr (Linux) to manually restore entries above.")


def main() -> int:
    parser = argparse.ArgumentParser(description="OS Switcher EFI Backup & Restore Utility")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json", help="Path to config.json")
    parser.add_argument("--dir", type=str, default="", help="Backup directory (overrides config)")
    parser.add_argument("--backup", action="store_true", help="Perform EFI backup")
    parser.add_argument("--list", action="store_true", help="List existing backups")
    parser.add_argument("--restore", type=str, help="Show manual restore instructions for a backup file")
    args = parser.parse_args()

    # Resolve backup directory
    backup_dir = args.dir
    os_name = platform.system().lower()

    if not backup_dir:
        try:
            config = validate(args.config)
            effective_key = (
                "windows_effective_state_dir" if os_name == "windows" else "linux_effective_state_dir"
            )
            backup_dir = str(config[effective_key])
        except Exception as exc:
            print(f"Error: Failed to load config to resolve state directory: {exc}", file=sys.stderr)
            return 1

    if args.backup:
        try:
            backup_path = backup_efi_entries(backup_dir, os_name)
            print(f"EFI backup successfully saved to: {backup_path}")
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    elif args.list:
        backups = list_backups(backup_dir)
        if not backups:
            print("No EFI backups found.")
        else:
            print(f"EFI Backups in {backup_dir} (newest first):")
            for b in backups:
                print(f"  - {b}")
    elif args.restore:
        try:
            restore_efi_backup(args.restore)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
