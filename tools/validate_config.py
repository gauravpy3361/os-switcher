#!/usr/bin/env python3
"""Validate OS Switcher config and optionally export shell variables."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


def fail(message: str) -> None:
    raise ConfigError(f"Config error: {message}")


def require_mapping(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key)
    if not isinstance(value, dict):
        fail(f"{key} must be an object")
    return value


def optional_mapping(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key, {})
    if not isinstance(value, dict):
        fail(f"{key} must be an object")
    return value


def require_text(section: dict[str, Any], dotted_key: str) -> str:
    key = dotted_key.rsplit(".", 1)[-1]
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(f"{dotted_key} must be a non-empty string")
    return value


def optional_text(section: dict[str, Any], dotted_key: str, default: str = "") -> str:
    key = dotted_key.rsplit(".", 1)[-1]
    value = section.get(key, default)
    if not isinstance(value, str):
        fail(f"{dotted_key} must be a string")
    return value


def require_int(section: dict[str, Any], dotted_key: str, default: int, minimum: int = 0) -> int:
    key = dotted_key.rsplit(".", 1)[-1]
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        fail(f"{dotted_key} must be an integer >= {minimum}")
    return value


def require_bool(section: dict[str, Any], dotted_key: str, default: bool) -> bool:
    key = dotted_key.rsplit(".", 1)[-1]
    value = section.get(key, default)
    if not isinstance(value, bool):
        fail(f"{dotted_key} must be true or false")
    return value


def validate(path: Path) -> dict[str, Any]:
    if not path.exists():
        fail(f"{path} not found. Copy config.example.json to config.json and edit it first.")

    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")

    if not isinstance(config, dict):
        fail("config root must be an object")

    windows = require_mapping(config, "windows")
    linux = require_mapping(config, "linux")
    safety = require_mapping(config, "safety")
    state = optional_mapping(config, "state")
    shared = optional_mapping(state, "shared")

    state_mode = optional_text(state, "state.mode", default="local").strip().lower()
    if state_mode not in {"local", "shared"}:
        fail("state.mode must be either 'local' or 'shared'")

    windows_state_dir = require_text(windows, "windows.stateDir")
    linux_state_dir = require_text(linux, "linux.stateDir")
    windows_shared_state_dir = optional_text(
        shared, "state.shared.windowsStateDir", default=""
    ).strip()
    linux_shared_state_dir = optional_text(shared, "state.shared.linuxStateDir", default="").strip()

    if state_mode == "shared":
        if not windows_shared_state_dir:
            fail("state.shared.windowsStateDir must be set when state.mode is 'shared'")
        if not linux_shared_state_dir:
            fail("state.shared.linuxStateDir must be set when state.mode is 'shared'")

    windows_effective_state_dir = (
        windows_shared_state_dir if state_mode == "shared" else windows_state_dir
    )
    linux_effective_state_dir = linux_shared_state_dir if state_mode == "shared" else linux_state_dir

    normalized = {
        "windows_target_label": require_text(windows, "windows.targetLabel"),
        "windows_reboot_timeout_seconds": require_int(
            windows, "windows.rebootTimeoutSeconds", default=5
        ),
        "windows_state_dir": windows_state_dir,
        "linux_target_label": require_text(linux, "linux.targetLabel"),
        "linux_reboot_delay_seconds": require_int(linux, "linux.rebootDelaySeconds", default=5),
        "linux_state_dir": linux_state_dir,
        "require_confirmation": require_bool(safety, "safety.requireConfirmation", default=True),
        "pending_transition_timeout_minutes": require_int(
            safety, "safety.pendingTransitionTimeoutMinutes", default=10, minimum=1
        ),
        "max_boot_failures": require_int(safety, "safety.maxBootFailures", default=3, minimum=1),
        "state_mode": state_mode,
        "shared_state_enabled": state_mode == "shared",
        "windows_shared_state_dir": windows_shared_state_dir,
        "linux_shared_state_dir": linux_shared_state_dir,
        "windows_effective_state_dir": windows_effective_state_dir,
        "linux_effective_state_dir": linux_effective_state_dir,
    }

    return normalized


def env_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9_]", "_", name.upper())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path", type=Path)
    parser.add_argument("--shell", action="store_true", help="print bash assignments")
    args = parser.parse_args()

    try:
        normalized = validate(args.config_path)
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc

    if args.shell:
        for key, value in normalized.items():
            if isinstance(value, bool):
                rendered = "1" if value else "0"
            else:
                rendered = str(value)
            print(f"{env_name(key)}={shlex.quote(rendered)}")
    else:
        json.dump(normalized, sys.stdout, indent=2)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
