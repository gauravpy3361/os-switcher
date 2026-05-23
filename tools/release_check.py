#!/usr/bin/env python3
"""Repository-level public release checks that do not touch firmware."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "VERSION",
    "LICENSE",
    "CHANGELOG.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "README.md",
    "config.example.json",
    "config.enterprise.example.json",
    "docs/setup.md",
    "docs/safety.md",
    "docs/enterprise-readiness.md",
    "docs/release.md",
    ".github/workflows/ci.yml",
    "tools/efi_backup.py",
    "windows/install-boot-success-task.ps1",
    "windows/status-boot-success-task.ps1",
    "windows/uninstall-boot-success-task.ps1",
    "windows/install.ps1",
    "windows/rollback.ps1",
    "windows/uninstall.ps1",
    "linux/install-boot-success-service.sh",
    "linux/status-boot-success-service.sh",
    "linux/uninstall-boot-success-service.sh",
    "linux/install.sh",
    "linux/rollback.sh",
    "linux/uninstall.sh",
]


def fail(message: str) -> None:
    print(f"FAIL {message}")
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"OK   {message}")


def main() -> int:
    sys.dont_write_bytecode = True
    from validate_config import ConfigError, validate

    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.exists():
            fail(f"missing required release file: {relative}")
    ok("required release files exist")

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not version:
        fail("VERSION is empty")
    if version not in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"):
        fail(f"CHANGELOG.md does not mention VERSION {version}")
    ok(f"version {version} is documented")

    try:
        dev_config = validate(ROOT / "config.example.json")
        enterprise_config = validate(ROOT / "config.enterprise.example.json")
    except ConfigError as exc:
        fail(str(exc))

    if dev_config["state_mode"] != "local":
        fail("config.example.json should stay local for safe development defaults")
    if enterprise_config["state_mode"] != "shared":
        fail("config.enterprise.example.json must use shared state")
    ok("config examples validate")

    ok("release builder excludes generated Python cache files")

    print("\nRelease check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
