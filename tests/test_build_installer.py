from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.build_installer import find_iscc, main


def test_find_iscc_in_path() -> None:
    with patch("tools.build_installer.shutil.which", return_value="C:\\Program Files\\Inno Setup 6\\ISCC.exe"):
        iscc = find_iscc()
        assert iscc is not None
        assert iscc.name == "ISCC.exe"


def test_find_iscc_in_candidates(tmp_path: Path) -> None:
    fake_iscc = tmp_path / "Inno Setup 6" / "ISCC.exe"
    fake_iscc.parent.mkdir(parents=True)
    fake_iscc.write_text("", encoding="utf-8")

    with patch("tools.build_installer.shutil.which", return_value=None), \
         patch("tools.build_installer.os.environ.get", return_value=str(tmp_path)):
        iscc = find_iscc()
        assert iscc is not None
        assert iscc.name == "ISCC.exe"
        assert iscc.exists()


def test_find_iscc_not_found() -> None:
    with patch("tools.build_installer.shutil.which", return_value=None), \
         patch("tools.build_installer.os.environ.get", return_value="C:\\NonExistentPath"):
        iscc = find_iscc()
        assert iscc is None


def test_build_installer_non_windows() -> None:
    with patch("tools.build_installer.sys.platform", "linux"):
        exit_code = main()
        assert exit_code == 1


def test_build_installer_missing_compiler() -> None:
    with patch("tools.build_installer.sys.platform", "win32"), \
         patch("tools.build_installer.find_iscc", return_value=None):
        exit_code = main()
        assert exit_code == 1


def test_build_installer_successful_run(tmp_path: Path) -> None:
    fake_iscc = tmp_path / "ISCC.exe"
    fake_iscc.write_text("", encoding="utf-8")

    fake_iss = tmp_path / "windows" / "OSSwitcher-Setup.iss"
    fake_iss.parent.mkdir(parents=True)
    fake_iss.write_text("", encoding="utf-8")

    mock_run = MagicMock()
    mock_run.returncode = 0

    with patch("tools.build_installer.sys.platform", "win32"), \
         patch("tools.build_installer.find_iscc", return_value=fake_iscc), \
         patch("tools.build_installer.ROOT", tmp_path), \
         patch("tools.build_installer.subprocess.run", return_value=mock_run) as mock_subprocess:
        
        exit_code = main()
        assert exit_code == 0
        mock_subprocess.assert_called_once()
        assert (tmp_path / "dist").exists()
