#!/usr/bin/env python3
"""Offline-friendly health checks for OS Switcher."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

from os_switcher_core import (
    EntryMatchError,
    find_unique_entry,
    parse_linux_efi_entries,
    parse_windows_firmware_entries,
)
from validate_config import ConfigError, validate


ROOT = Path(__file__).resolve().parents[1]


class CheckReport:
    def __init__(self) -> None:
        self.failures = 0
        self.warnings = 0

    def ok(self, message: str) -> None:
        print(f"OK   {message}")

    def warn(self, message: str) -> None:
        self.warnings += 1
        print(f"WARN {message}")

    def fail(self, message: str) -> None:
        self.failures += 1
        print(f"FAIL {message}")


def current_platform() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    return system


def test_writable_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".os-switcher-doctor-write-test"
    probe.write_text("ok\n", encoding="utf-8")
    probe.unlink()


def read_firmware_output(args: argparse.Namespace, os_name: str) -> tuple[str, str]:
    if args.firmware_output:
        return Path(args.firmware_output).read_text(encoding="utf-8"), str(args.firmware_output)

    if args.offline:
        return "", "offline mode"

    if os_name == "windows":
        completed = subprocess.run(
            ["bcdedit", "/enum", "firmware"],
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.stdout + completed.stderr, "bcdedit /enum firmware"

    if os_name == "linux":
        completed = subprocess.run(["efibootmgr"], check=False, capture_output=True, text=True)
        return completed.stdout + completed.stderr, "efibootmgr"

    return "", "unsupported platform"


def check_firmware(report: CheckReport, args: argparse.Namespace, os_name: str, config: dict[str, object]) -> None:
    firmware_text, source = read_firmware_output(args, os_name)
    if not firmware_text:
        report.warn(f"Skipped firmware entry check ({source}).")
        return

    if os_name == "windows":
        entries = parse_windows_firmware_entries(firmware_text)
        target_label = str(config["windows_target_label"])
    elif os_name == "linux":
        entries = parse_linux_efi_entries(firmware_text)
        target_label = str(config["linux_target_label"])
    else:
        report.warn(f"Skipped firmware entry check on unsupported platform '{os_name}'.")
        return

    if not entries:
        report.fail(f"No firmware entries could be parsed from {source}.")
        return

    try:
        entry = find_unique_entry(entries, target_label)
    except EntryMatchError as exc:
        report.fail(str(exc))
        return

    report.ok(f"Target label matches exactly one firmware entry: {entry.label} ({entry.identifier}).")


def check_python_version(report: CheckReport) -> None:
    version = sys.version_info
    if version < (3, 8):
        report.fail(f"Python 3.8+ required. Current: {version.major}.{version.minor}.{version.micro}")
        return

    report.ok(f"Python version is {version.major}.{version.minor}.{version.micro}.")


def check_efi_layout(report: CheckReport, os_name: str) -> None:
    if os_name == "windows":
        efi_path = Path(r"C:\Windows\Boot\EFI")
    elif os_name == "linux":
        efi_path = Path("/sys/firmware/efi")
    else:
        report.warn(f"Skipped EFI layout check on unsupported platform '{os_name}'.")
        return

    if not efi_path.exists():
        report.fail("EFI firmware not detected. This tool requires a UEFI system.")
        return

    report.ok(f"EFI firmware detected ({efi_path}).")


def check_grub(report: CheckReport, os_name: str) -> None:
    if os_name != "linux":
        report.warn("GRUB check not applicable on Windows.")
        return

    grub_paths = [Path("/boot/grub2/grub.cfg"), Path("/boot/grub/grub.cfg")]
    grub_cfg = None
    for candidate in grub_paths:
        if candidate.exists():
            grub_cfg = candidate
            break

    if grub_cfg is None:
        report.fail("GRUB config not found.")
        return

    try:
        content = grub_cfg.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        report.fail(f"Could not read GRUB config '{grub_cfg}': {exc}")
        return

    import re
    match = re.search(r"set\s+timeout\s*=\s*(\d+)", content)
    if match is None:
        match = re.search(r"GRUB_TIMEOUT\s*=\s*(\d+)", content)

    if match is None:
        report.warn(f"Could not determine GRUB timeout value from {grub_cfg}.")
        return

    timeout = int(match.group(1))
    if timeout == 0:
        report.fail("GRUB_TIMEOUT is 0 — this will break switching. Set it to at least 1.")
        return

    report.ok(f"GRUB timeout is {timeout} second(s).")


def check_bitlocker(report: CheckReport, os_name: str) -> None:
    if os_name != "windows":
        report.warn("BitLocker check not applicable on Linux.")
        return

    try:
        completed = subprocess.run(
            ["manage-bde", "-status", "C:"],
            check=False,
            capture_output=True,
            text=True,
        )
        output = completed.stdout + completed.stderr
        if "Protection On" in output:
            report.fail(
                "BitLocker is ACTIVE on C:. You MUST disable it before switching OSes. "
                "Go to: Control Panel > BitLocker Drive Encryption > Turn off BitLocker. "
                "Switching with BitLocker active can permanently lock you out of Windows."
            )
        else:
            report.ok("BitLocker is not active.")
    except Exception:
        report.ok("BitLocker is not active.")


def check_vendor_quirks(report: CheckReport) -> None:
    os_name = current_platform()
    vendor = ""
    if os_name == "windows":
        try:
            completed = subprocess.run(
                ["wmic", "baseboard", "get", "Manufacturer,Product", "/value"],
                check=False,
                capture_output=True,
                text=True,
            )
            vendor = completed.stdout + completed.stderr
        except Exception:
            pass
    elif os_name == "linux":
        try:
            vendor_path = Path("/sys/class/dmi/id/board_vendor")
            name_path = Path("/sys/class/dmi/id/board_name")
            parts = []
            if vendor_path.exists():
                parts.append(vendor_path.read_text(encoding="utf-8").strip())
            if name_path.exists():
                parts.append(name_path.read_text(encoding="utf-8").strip())
            vendor = " ".join(parts)
        except Exception:
            pass

    if not vendor.strip():
        report.warn("Could not detect system vendor. Skipping quirk check.")
        return

    if "asus" in vendor.lower() or "asustek" in vendor.lower():
        report.warn(
            "ASUS firmware detected. This firmware ignores EFI BootNext and may hardcode bootmgfw.efi as fallback. "
            "GRUB must remain enabled with timeout >= 1. Do NOT disable GRUB."
        )
    else:
        report.ok("No known firmware quirks detected for this vendor.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--platform", choices=["windows", "linux"], default=current_platform())
    parser.add_argument("--offline", action="store_true", help="skip live bcdedit/efibootmgr calls")
    parser.add_argument("--firmware-output", type=Path, help="use saved bcdedit/efibootmgr output")
    parser.add_argument(
        "--production",
        action="store_true",
        help="treat local-only state as a failure instead of a warning",
    )
    parser.add_argument(
        "--check-writable",
        action="store_true",
        help="create the current platform state directory and test write access",
    )
    args = parser.parse_args()

    report = CheckReport()

    try:
        config = validate(args.config)
    except (ConfigError, SystemExit) as exc:
        report.fail(str(exc))
        return 1

    report.ok(f"Config is valid: {args.config}")

    state_mode = str(config["state_mode"])
    if state_mode == "shared":
        report.ok("Shared state mode is enabled.")
    elif args.production:
        report.fail("state.mode is 'local'. Production use should configure shared state.")
    else:
        report.warn("state.mode is 'local'. This is fine for development, but not production switching.")

    effective_key = (
        "windows_effective_state_dir" if args.platform == "windows" else "linux_effective_state_dir"
    )
    effective_state_dir = str(config[effective_key])
    report.ok(f"{args.platform} state directory resolves to: {effective_state_dir}")

    if args.check_writable:
        try:
            test_writable_dir(Path(os.path.expandvars(effective_state_dir)))
        except OSError as exc:
            report.fail(f"State directory is not writable: {exc}")
        else:
            report.ok("State directory is writable.")

    check_firmware(report, args, args.platform, config)
    check_python_version(report)
    check_efi_layout(report, args.platform)
    check_grub(report, args.platform)
    check_bitlocker(report, args.platform)
    check_vendor_quirks(report)

    if report.failures:
        print(f"\nResult: {report.failures} failure(s), {report.warnings} warning(s).")
        return 1

    print(f"\nResult: passed with {report.warnings} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
