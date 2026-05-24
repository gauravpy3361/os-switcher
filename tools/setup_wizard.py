#!/usr/bin/env python3
"""Interactive setup wizard for OS Switcher."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

# Add tools to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from os_switcher_core import (
    BootEntry,
    parse_linux_efi_entries,
    parse_windows_firmware_entries,
)


def current_platform() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    return system


def detect_efi_entries(os_name: str) -> list[BootEntry]:
    if os_name == "windows":
        try:
            completed = subprocess.run(
                ["bcdedit", "/enum", "firmware"],
                capture_output=True,
                text=True,
                check=False,
            )
            # bcdedit returns a non-zero exit code if not running as administrator
            if completed.returncode != 0:
                print(f"Error: bcdedit command failed (exit code {completed.returncode}).", file=sys.stderr)
                print(f"Error details: {completed.stderr.strip()}", file=sys.stderr)
                sys.exit(1)
            entries = parse_windows_firmware_entries(completed.stdout)
            return entries
        except Exception as exc:
            print(f"Error: Failed to execute bcdedit: {exc}", file=sys.stderr)
            sys.exit(1)
    elif os_name == "linux":
        try:
            completed = subprocess.run(
                ["efibootmgr", "-v"],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                print(f"Error: efibootmgr command failed (exit code {completed.returncode}).", file=sys.stderr)
                print(f"Error details: {completed.stderr.strip()}", file=sys.stderr)
                sys.exit(1)
            entries = parse_linux_efi_entries(completed.stdout)
            return entries
        except Exception as exc:
            print(f"Error: Failed to execute efibootmgr: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error: Unsupported operating system platform '{os_name}'.", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    os_name = current_platform()
    if os_name == "windows":
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            is_admin = False
        if not is_admin:
            print("ERROR: This wizard must be run as Administrator.", file=sys.stderr)
            print("Right-click PowerShell and select 'Run as Administrator', then try again.", file=sys.stderr)
            sys.exit(1)
    elif os_name == "linux":
        try:
            import os
            is_root = os.geteuid() == 0
        except Exception:
            is_root = False
        if not is_root:
            print("ERROR: This wizard must be run as root.", file=sys.stderr)
            print("Run: sudo python3 tools/setup_wizard.py", file=sys.stderr)
            sys.exit(1)

    parser = argparse.ArgumentParser(description="OS Switcher Setup Wizard")
    parser.add_argument("-o", "--output", type=Path, help="Path to write the config.json file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be written without writing it")
    args = parser.parse_args()

    # STEP 1 — Welcome banner
    print("==========================================")
    print("OS Switcher Setup Wizard v1.0.0")
    print("This wizard will detect your boot entries and create config.json")
    print("==========================================\n")

    os_name = current_platform()

    # STEP 2 — Detect EFI entries
    print("Detecting EFI boot entries...")
    detected_entries = detect_efi_entries(os_name)

    entries = []
    for e in detected_entries:
        cleaned_label = e.label.split('\t')[0].strip()
        if cleaned_label:
            entries.append(BootEntry(identifier=e.identifier, label=cleaned_label, raw=e.raw))

    if not entries:
        print("Error: No boot entries could be parsed from the firmware output.", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully detected {len(entries)} boot entry/entries.\n")

    # STEP 3 — Show entries to user
    print("Detected Boot Entries:")
    for idx, entry in enumerate(entries, start=1):
        print(f"  [{idx}] {entry.label} (ID: {entry.identifier})")
    print("")

    # STEP 4 — Ask user to pick Windows entry
    while True:
        try:
            windows_input = input("Enter the number for your WINDOWS boot entry: ").strip()
            win_idx = int(windows_input)
            if 1 <= win_idx <= len(entries):
                windows_entry = entries[win_idx - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(entries)}.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # STEP 5 — Ask user to pick Linux entry
    while True:
        try:
            linux_input = input("Enter the number for your LINUX boot entry: ").strip()
            lin_idx = int(linux_input)
            if 1 <= lin_idx <= len(entries):
                if lin_idx == win_idx:
                    print("Error: The Linux boot entry must be different from the Windows boot entry.")
                    continue
                linux_entry = entries[lin_idx - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(entries)}.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    print("")

    # STEP 6 — Ask for state directory
    default_state_dir = "C:\\ProgramData\\OSSwitcher" if os_name == "windows" else "/var/lib/os-switcher"
    state_dir_input = input(f"State directory [{default_state_dir}]: ").strip()
    state_dir = state_dir_input if state_dir_input else default_state_dir

    print("")

    # STEP 7 — Show summary and confirm
    print("Configuration Summary:")
    print(f"  Windows entry: {windows_entry.label} ({windows_entry.identifier})")
    print(f"  Linux entry: {linux_entry.label} ({linux_entry.identifier})")
    print(f"  State directory: {state_dir}")
    print("")

    while True:
        confirm = input("Write config.json? (yes/no): ").strip().lower()
        if confirm in ("yes", "y"):
            break
        elif confirm in ("no", "n"):
            print("Setup cancelled by user. Exiting.")
            return 0
        else:
            print("Please enter 'yes' or 'no'.")

    # STEP 8 — Write config.json
    config_output_path = args.output if args.output else (ROOT / "config.json")

    # Load config.example.json as template
    example_path = ROOT / "config.example.json"
    if not example_path.exists():
        print(f"Error: Template config.example.json not found at {example_path}.", file=sys.stderr)
        return 1

    try:
        with open(example_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as exc:
        print(f"Error: Failed to read template config.example.json: {exc}", file=sys.stderr)
        return 1

    # Fill in template
    config_data["windows"]["bootEntryLabel"] = windows_entry.label
    config_data["linux"]["bootEntryLabel"] = linux_entry.label
    config_data["windows"]["targetLabel"] = linux_entry.label
    config_data["linux"]["targetLabel"] = windows_entry.label
    if os_name == "windows":
        config_data["windows"]["stateDir"] = state_dir
        config_data["linux"]["stateDir"] = "/var/lib/os-switcher"
    else:
        config_data["linux"]["stateDir"] = state_dir
        config_data["windows"]["stateDir"] = "C:\\ProgramData\\OSSwitcher"

    # Handle dry run or writing
    if args.dry_run:
        print("\n[DRY RUN] Would write following config.json content to:", config_output_path)
        print(json.dumps(config_data, indent=2))
        print("[DRY RUN] Dry run finished. No file was written.")
        return 0
    else:
        try:
            with open(config_output_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
                f.write("\n")
            print(f"\nconfig.json written successfully. You are ready to switch!")
        except Exception as exc:
            print(f"Error: Failed to write configuration to {config_output_path}: {exc}", file=sys.stderr)
            return 1

    # STEP 9 — Run doctor check
    print("\nRunning doctor check to verify configuration...")
    doctor_path = ROOT / "tools" / "doctor.py"
    try:
        completed = subprocess.run(
            [sys.executable, str(doctor_path), "--config", str(config_output_path)],
            check=False,
            text=True,
        )
    except Exception as exc:
        print(f"Error: Failed to run doctor check: {exc}", file=sys.stderr)
        return 1

    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
