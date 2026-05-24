from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.setup_wizard import current_platform, detect_efi_entries, main


def test_current_platform() -> None:
    with patch("tools.setup_wizard.platform.system", return_value="Windows"):
        assert current_platform() == "windows"
    with patch("tools.setup_wizard.platform.system", return_value="Linux"):
        assert current_platform() == "linux"
    with patch("tools.setup_wizard.platform.system", return_value="Darwin"):
        assert current_platform() == "darwin"


def test_detect_efi_entries_windows_success() -> None:
    mock_output = """
Firmware Boot Manager
---------------------
identifier              {fwbootmgr}
displayorder            {bootmgr}
                        {77777777-7777-7777-7777-777777777777}
timeout                 2

Windows Boot Manager
--------------------
identifier              {bootmgr}
device                  partition=\\Device\\HarddiskVolume1
description             Windows Boot Manager
locale                  en-US
"""
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = mock_output
    mock_run.stderr = ""

    with patch("tools.setup_wizard.subprocess.run", return_value=mock_run):
        entries = detect_efi_entries("windows")

    assert len(entries) == 2
    assert entries[0].identifier == "{fwbootmgr}"
    assert entries[1].identifier == "{bootmgr}"
    assert entries[1].label == "Windows Boot Manager"


def test_detect_efi_entries_windows_failure() -> None:
    mock_run = MagicMock()
    mock_run.returncode = 1
    mock_run.stdout = ""
    mock_run.stderr = "Access denied."

    with patch("tools.setup_wizard.subprocess.run", return_value=mock_run):
        with pytest.raises(SystemExit):
            detect_efi_entries("windows")


def test_detect_efi_entries_linux_success() -> None:
    mock_output = "BootCurrent: 0001\nBoot0000* Windows Boot Manager\nBoot0001* Fedora\n"
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = mock_output
    mock_run.stderr = ""

    with patch("tools.setup_wizard.subprocess.run", return_value=mock_run):
        entries = detect_efi_entries("linux")

    assert len(entries) == 2
    assert entries[0].identifier == "0000"
    assert entries[0].label == "Windows Boot Manager"
    assert entries[1].identifier == "0001"
    assert entries[1].label == "Fedora"


def test_detect_efi_entries_linux_failure() -> None:
    mock_run = MagicMock()
    mock_run.returncode = 1
    mock_run.stdout = ""
    mock_run.stderr = "efibootmgr not found"

    with patch("tools.setup_wizard.subprocess.run", return_value=mock_run):
        with pytest.raises(SystemExit):
            detect_efi_entries("linux")


def test_setup_wizard_dry_run_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_output = "BootCurrent: 0001\nBoot0000* Windows Boot Manager\nBoot0001* Fedora\n"
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = mock_output
    mock_run.stderr = ""

    # Mock inputs:
    # 1. Windows entry index -> 1 (Windows Boot Manager)
    # 2. Linux entry index -> 2 (Fedora)
    # 3. State directory -> press enter (use default)
    # 4. Confirmation -> yes
    inputs = ["1", "2", "", "yes"]
    input_generator = (val for val in inputs)

    def mock_input(prompt: str = "") -> str:
        return next(input_generator)

    # Prepare temp example file and output path
    example_config = {
        "windows": {
            "targetLabel": "Placeholder",
            "rebootTimeoutSeconds": 5,
            "stateDir": "C:\\ProgramData\\OSSwitcher"
        },
        "linux": {
            "targetLabel": "Placeholder",
            "rebootDelaySeconds": 5,
            "stateDir": "/var/lib/os-switcher"
        },
        "state": {
            "mode": "local",
            "shared": {
                "windowsStateDir": "",
                "linuxStateDir": ""
            }
        },
        "safety": {
            "requireConfirmation": True,
            "pendingTransitionTimeoutMinutes": 10,
            "maxBootFailures": 3
        }
    }
    example_path = tmp_path / "config.example.json"
    example_path.write_text(json.dumps(example_config), encoding="utf-8")

    output_path = tmp_path / "config.json"

    # Patch modules and run
    with patch("tools.setup_wizard.platform.system", return_value="Linux"), \
         patch("tools.setup_wizard.subprocess.run", return_value=mock_run), \
         patch("builtins.input", mock_input), \
         patch("tools.setup_wizard.ROOT", tmp_path), \
         patch("os.geteuid", return_value=0, create=True):
        
        args = ["setup_wizard.py", "--output", str(output_path), "--dry-run"]
        monkeypatch.setattr(sys, "argv", args)
        
        exit_code = main()
        assert exit_code == 0
        assert not output_path.exists()  # dry-run should not write


def test_setup_wizard_write_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_output = "BootCurrent: 0001\nBoot0000* Windows Boot Manager\nBoot0001* Fedora\n"
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = mock_output
    mock_run.stderr = ""

    inputs = ["1", "2", "/custom/state/dir", "yes"]
    input_generator = (val for val in inputs)

    def mock_input(prompt: str = "") -> str:
        return next(input_generator)

    example_config = {
        "windows": {
            "targetLabel": "Placeholder",
            "rebootTimeoutSeconds": 5,
            "stateDir": "C:\\ProgramData\\OSSwitcher"
        },
        "linux": {
            "targetLabel": "Placeholder",
            "rebootDelaySeconds": 5,
            "stateDir": "/var/lib/os-switcher"
        },
        "state": {
            "mode": "local"
        },
        "safety": {
            "requireConfirmation": True,
            "pendingTransitionTimeoutMinutes": 10,
            "maxBootFailures": 3
        }
    }
    example_path = tmp_path / "config.example.json"
    example_path.write_text(json.dumps(example_config), encoding="utf-8")

    output_path = tmp_path / "config.json"

    doctor_mock = MagicMock()
    doctor_mock.returncode = 0

    with patch("tools.setup_wizard.platform.system", return_value="Linux"), \
         patch("tools.setup_wizard.subprocess.run", side_effect=[mock_run, doctor_mock]), \
         patch("builtins.input", mock_input), \
         patch("tools.setup_wizard.ROOT", tmp_path), \
         patch("os.geteuid", return_value=0, create=True):
        
        args = ["setup_wizard.py", "--output", str(output_path)]
        monkeypatch.setattr(sys, "argv", args)
        
        exit_code = main()
        assert exit_code == 0
        assert output_path.exists()

        # Read config and assert fields
        written_config = json.loads(output_path.read_text(encoding="utf-8"))
        assert written_config["windows"]["bootEntryLabel"] == "Windows Boot Manager"
        assert written_config["linux"]["bootEntryLabel"] == "Fedora"
        assert written_config["windows"]["targetLabel"] == "Fedora"
        assert written_config["linux"]["targetLabel"] == "Windows Boot Manager"
        assert written_config["windows"]["stateDir"] == "/custom/state/dir"
        assert written_config["linux"]["stateDir"] == "/custom/state/dir"


def test_setup_wizard_requires_admin_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch("tools.setup_wizard.platform.system", return_value="Windows"), \
         patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=0, create=True):
        
        args = ["setup_wizard.py"]
        monkeypatch.setattr(sys, "argv", args)
        
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1


def test_setup_wizard_requires_root_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch("tools.setup_wizard.platform.system", return_value="Linux"), \
         patch("os.geteuid", return_value=1000, create=True):
        
        args = ["setup_wizard.py"]
        monkeypatch.setattr(sys, "argv", args)
        
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1


def test_setup_wizard_filters_and_truncates_labels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Boot0000 has a clean label
    # Boot0001 has a tab and path in the label
    # Boot0002 has an empty label (should be filtered out)
    mock_output = "BootCurrent: 0001\nBoot0000* Windows Boot Manager\nBoot0001* Fedora\tHD(1,GPT,...)\nBoot0002* \n"
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = mock_output
    mock_run.stderr = ""

    # Inputs:
    # 1. Windows entry -> 1 (Windows Boot Manager)
    # 2. Linux entry -> 2 (Fedora)
    # 3. State directory -> default
    # 4. Confirm -> yes
    inputs = ["1", "2", "", "yes"]
    input_generator = (val for val in inputs)

    def mock_input(prompt: str = "") -> str:
        return next(input_generator)

    example_config = {
        "windows": {
            "targetLabel": "Placeholder",
            "stateDir": ""
        },
        "linux": {
            "targetLabel": "Placeholder",
            "stateDir": ""
        },
        "state": {
            "mode": "local"
        },
        "safety": {
            "requireConfirmation": True,
            "pendingTransitionTimeoutMinutes": 10,
            "maxBootFailures": 3
        }
    }
    example_path = tmp_path / "config.example.json"
    example_path.write_text(json.dumps(example_config), encoding="utf-8")

    output_path = tmp_path / "config.json"

    doctor_mock = MagicMock()
    doctor_mock.returncode = 0

    with patch("tools.setup_wizard.platform.system", return_value="Linux"), \
         patch("tools.setup_wizard.subprocess.run", side_effect=[mock_run, doctor_mock]), \
         patch("builtins.input", mock_input), \
         patch("tools.setup_wizard.ROOT", tmp_path), \
         patch("os.geteuid", return_value=0, create=True):
        
        args = ["setup_wizard.py", "--output", str(output_path)]
        monkeypatch.setattr(sys, "argv", args)
        
        exit_code = main()
        assert exit_code == 0
        assert output_path.exists()

        # Read config and assert fields are correctly truncated and filtered
        written_config = json.loads(output_path.read_text(encoding="utf-8"))
        assert written_config["windows"]["bootEntryLabel"] == "Windows Boot Manager"
        assert written_config["linux"]["bootEntryLabel"] == "Fedora"  # tab and device path stripped!
        assert written_config["windows"]["targetLabel"] == "Fedora"
        assert written_config["linux"]["targetLabel"] == "Windows Boot Manager"

