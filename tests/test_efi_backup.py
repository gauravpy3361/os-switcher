from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.efi_backup import backup_efi_entries, list_backups, restore_efi_backup


# ---------------------------------------------------------------------------
# backup_efi_entries
# ---------------------------------------------------------------------------


def test_backup_efi_entries_linux_writes_file(tmp_path: Path) -> None:
    fake_output = "BootCurrent: 0001\nBoot0000* Windows Boot Manager\nBoot0001* Fedora\n"
    mock_result = MagicMock()
    mock_result.stdout = fake_output
    mock_result.stderr = ""

    with patch("tools.efi_backup.subprocess.run", return_value=mock_result):
        backup_path = backup_efi_entries(str(tmp_path), "linux")

    assert Path(backup_path).exists()
    assert "efi-backup-" in Path(backup_path).name
    assert Path(backup_path).read_text(encoding="utf-8") == fake_output


def test_backup_efi_entries_windows_writes_file(tmp_path: Path) -> None:
    fake_output = "Firmware Boot Manager\n----------\nidentifier  {bootmgr}\n"
    mock_result = MagicMock()
    mock_result.stdout = fake_output
    mock_result.stderr = ""

    with patch("tools.efi_backup.subprocess.run", return_value=mock_result):
        backup_path = backup_efi_entries(str(tmp_path), "windows")

    assert Path(backup_path).exists()
    content = Path(backup_path).read_text(encoding="utf-8")
    assert "bootmgr" in content


def test_backup_efi_entries_unsupported_os_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Unsupported OS"):
        backup_efi_entries(str(tmp_path), "darwin")


def test_backup_efi_entries_command_failure_raises(tmp_path: Path) -> None:
    with patch(
        "tools.efi_backup.subprocess.run",
        side_effect=subprocess.SubprocessError("command failed"),
    ):
        with pytest.raises(RuntimeError, match="Command failed"):
            backup_efi_entries(str(tmp_path), "linux")


# ---------------------------------------------------------------------------
# list_backups
# ---------------------------------------------------------------------------


def test_list_backups_returns_newest_first(tmp_path: Path) -> None:
    # Create files with different names (timestamp-ordered)
    (tmp_path / "efi-backup-20260101-100000.txt").write_text("a")
    (tmp_path / "efi-backup-20260101-120000.txt").write_text("b")
    (tmp_path / "efi-backup-20260101-110000.txt").write_text("c")

    result = list_backups(str(tmp_path))

    assert len(result) == 3
    # Newest (lexicographically last by filename) should be first
    assert "120000" in result[0]
    assert "100000" in result[-1]


def test_list_backups_ignores_non_backup_files(tmp_path: Path) -> None:
    (tmp_path / "efi-backup-20260101-100000.txt").write_text("a")
    (tmp_path / "recovery-mode.json").write_text("{}")
    (tmp_path / "pending-transition.json").write_text("{}")

    result = list_backups(str(tmp_path))

    assert len(result) == 1


def test_list_backups_missing_dir_returns_empty() -> None:
    result = list_backups("/nonexistent/path/that/cannot/exist")
    assert result == []


# ---------------------------------------------------------------------------
# restore_efi_backup
# ---------------------------------------------------------------------------


def test_restore_efi_backup_prints_contents(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    backup_file = tmp_path / "efi-backup-20260101-100000.txt"
    backup_file.write_text("Boot0000* Windows Boot Manager\nBoot0001* Fedora\n", encoding="utf-8")

    restore_efi_backup(str(backup_file))

    captured = capsys.readouterr()
    assert "EFI BACKUP CONTENTS" in captured.out
    assert "Windows Boot Manager" in captured.out
    assert "manually restore" in captured.out.lower()


def test_restore_efi_backup_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        restore_efi_backup(str(tmp_path / "does_not_exist.txt"))
