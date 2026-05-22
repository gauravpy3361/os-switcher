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

    if report.failures:
        print(f"\nResult: {report.failures} failure(s), {report.warnings} warning(s).")
        return 1

    print(f"\nResult: passed with {report.warnings} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
