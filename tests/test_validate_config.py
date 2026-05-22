from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.validate_config import ConfigError, validate


def write_config(path: Path, **overrides: object) -> Path:
    config: dict[str, object] = {
        "windows": {
            "targetLabel": "Linux Workspace",
            "rebootTimeoutSeconds": 5,
            "stateDir": "C:\\ProgramData\\OSSwitcher",
        },
        "linux": {
            "targetLabel": "Windows Boot Manager",
            "rebootDelaySeconds": 5,
            "stateDir": "/var/lib/os-switcher",
        },
        "safety": {
            "requireConfirmation": True,
            "pendingTransitionTimeoutMinutes": 10,
            "maxBootFailures": 3,
        },
    }
    config.update(overrides)
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_local_state_defaults_to_platform_state_dirs(tmp_path: Path) -> None:
    normalized = validate(write_config(tmp_path / "config.json"))

    assert normalized["state_mode"] == "local"
    assert normalized["shared_state_enabled"] is False
    assert normalized["windows_effective_state_dir"] == "C:\\ProgramData\\OSSwitcher"
    assert normalized["linux_effective_state_dir"] == "/var/lib/os-switcher"


def test_shared_state_uses_platform_mapped_paths(tmp_path: Path) -> None:
    normalized = validate(
        write_config(
            tmp_path / "config.json",
            state={
                "mode": "shared",
                "shared": {
                    "windowsStateDir": "D:\\OSSwitcherState",
                    "linuxStateDir": "/mnt/os-switcher-state",
                },
            },
        )
    )

    assert normalized["shared_state_enabled"] is True
    assert normalized["windows_effective_state_dir"] == "D:\\OSSwitcherState"
    assert normalized["linux_effective_state_dir"] == "/mnt/os-switcher-state"


def test_shared_state_requires_both_platform_paths(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / "config.json",
        state={"mode": "shared", "shared": {"windowsStateDir": "D:\\OSSwitcherState"}},
    )

    with pytest.raises(ConfigError, match="linuxStateDir"):
        validate(config_path)


def test_rejects_unknown_state_mode(tmp_path: Path) -> None:
    config_path = write_config(tmp_path / "config.json", state={"mode": "magic"})

    with pytest.raises(ConfigError, match="state.mode"):
        validate(config_path)
