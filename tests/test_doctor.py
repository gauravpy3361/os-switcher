from __future__ import annotations

import argparse
import datetime
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.doctor import (
    CheckReport,
    check_bitlocker,
    check_efi_layout,
    check_grub,
    check_python_version,
    check_stale_transitions,
    check_vendor_quirks,
)


# ---------------------------------------------------------------------------
# check_python_version
# ---------------------------------------------------------------------------


def test_check_python_version_passes_on_current() -> None:
    report = CheckReport()
    check_python_version(report)
    # Running on Python 3.8+ (CI enforces this), so no failures
    assert report.failures == 0


def test_check_python_version_fails_below_38(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    from collections import namedtuple

    FakeVersion = namedtuple('version_info', ['major', 'minor', 'micro', 'releaselevel', 'serial'])
    monkeypatch.setattr(sys, "version_info", FakeVersion(2, 7, 18, 'final', 0))

    report = CheckReport()
    check_python_version(report)

    assert report.failures == 1


# ---------------------------------------------------------------------------
# check_efi_layout
# ---------------------------------------------------------------------------


def test_check_efi_layout_linux_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    efi_dir = tmp_path / "sys" / "firmware" / "efi"
    efi_dir.mkdir(parents=True)

    # Patch Path to return our fake efi path for the linux check
    with patch("tools.doctor.Path") as mock_path_cls:
        # Make Path("/sys/firmware/efi") return existing dir
        fake_path = MagicMock()
        fake_path.exists.return_value = True
        mock_path_cls.return_value = fake_path

        report = CheckReport()
        check_efi_layout(report, "linux")

    assert report.failures == 0


def test_check_efi_layout_linux_fails_when_missing() -> None:
    with patch("tools.doctor.Path") as mock_path_cls:
        fake_path = MagicMock()
        fake_path.exists.return_value = False
        mock_path_cls.return_value = fake_path

        report = CheckReport()
        check_efi_layout(report, "linux")

    assert report.failures == 1


def test_check_efi_layout_unsupported_platform_warns() -> None:
    report = CheckReport()
    check_efi_layout(report, "darwin")
    assert report.warnings == 1
    assert report.failures == 0


# ---------------------------------------------------------------------------
# check_grub
# ---------------------------------------------------------------------------


def test_check_grub_skipped_on_windows() -> None:
    report = CheckReport()
    check_grub(report, "windows")
    assert report.warnings == 1
    assert report.failures == 0


def test_check_grub_ok_when_timeout_nonzero(tmp_path: Path) -> None:
    grub_cfg = tmp_path / "grub.cfg"
    grub_cfg.write_text("set timeout=5\n", encoding="utf-8")

    with patch("tools.doctor.Path") as mock_path_cls:
        # First call (grub2 path) returns non-existent
        # Second call (grub path) returns our file
        fake_missing = MagicMock()
        fake_missing.exists.return_value = False
        fake_found = MagicMock()
        fake_found.exists.return_value = True
        fake_found.read_text.return_value = "set timeout=5\n"
        mock_path_cls.side_effect = [fake_missing, fake_found]

        report = CheckReport()
        check_grub(report, "linux")

    assert report.failures == 0


def test_check_grub_fails_when_timeout_zero(tmp_path: Path) -> None:
    with patch("tools.doctor.Path") as mock_path_cls:
        fake_missing = MagicMock()
        fake_missing.exists.return_value = False
        fake_found = MagicMock()
        fake_found.exists.return_value = True
        fake_found.read_text.return_value = "set timeout=0\n"
        mock_path_cls.side_effect = [fake_missing, fake_found]

        report = CheckReport()
        check_grub(report, "linux")

    assert report.failures == 1


def test_check_grub_fails_when_config_missing() -> None:
    with patch("tools.doctor.Path") as mock_path_cls:
        fake_missing = MagicMock()
        fake_missing.exists.return_value = False
        mock_path_cls.side_effect = [fake_missing, fake_missing]

        report = CheckReport()
        check_grub(report, "linux")

    assert report.failures == 1


# ---------------------------------------------------------------------------
# check_bitlocker
# ---------------------------------------------------------------------------


def test_check_bitlocker_skipped_on_linux() -> None:
    report = CheckReport()
    check_bitlocker(report, "linux")
    assert report.warnings == 1
    assert report.failures == 0


@pytest.mark.hardware
def test_check_bitlocker_fails_when_protection_on() -> None:
    mock_result = MagicMock()
    mock_result.stdout = "Protection Status:     Protection On\n"
    mock_result.stderr = ""

    with patch("tools.doctor.subprocess.run", return_value=mock_result):
        report = CheckReport()
        check_bitlocker(report, "windows")

    assert report.failures == 1


@pytest.mark.hardware
def test_check_bitlocker_ok_when_protection_off() -> None:
    mock_result = MagicMock()
    mock_result.stdout = "Protection Status:     Protection Off\n"
    mock_result.stderr = ""

    with patch("tools.doctor.subprocess.run", return_value=mock_result):
        report = CheckReport()
        check_bitlocker(report, "windows")

    assert report.failures == 0
    assert report.warnings == 0


@pytest.mark.hardware
def test_check_bitlocker_warns_when_manage_bde_absent() -> None:
    with patch(
        "tools.doctor.subprocess.run",
        side_effect=FileNotFoundError("manage-bde not found"),
    ):
        report = CheckReport()
        check_bitlocker(report, "windows")

    # Should warn, not fail — absent tool ≠ confirmed safe
    assert report.warnings == 1
    assert report.failures == 0


# ---------------------------------------------------------------------------
# check_vendor_quirks
# ---------------------------------------------------------------------------


def test_check_vendor_quirks_warns_on_asus_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.doctor as doctor_module

    monkeypatch.setattr(doctor_module, "current_platform", lambda: "linux")

    asus_vendor = MagicMock()
    asus_vendor.exists.return_value = True
    asus_vendor.read_text.return_value = "ASUSTeK COMPUTER INC."

    product_name = MagicMock()
    product_name.exists.return_value = True
    product_name.read_text.return_value = "ASUS ROG STRIX"

    with patch("tools.doctor.Path", side_effect=[asus_vendor, product_name]):
        report = CheckReport()
        check_vendor_quirks(report)

    assert report.warnings == 1


def test_check_vendor_quirks_ok_for_unknown_vendor_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tools.doctor as doctor_module

    monkeypatch.setattr(doctor_module, "current_platform", lambda: "linux")

    vendor_path = MagicMock()
    vendor_path.exists.return_value = True
    vendor_path.read_text.return_value = "Lenovo"

    product_path = MagicMock()
    product_path.exists.return_value = True
    product_path.read_text.return_value = "ThinkPad X1"

    with patch("tools.doctor.Path", side_effect=[vendor_path, product_path]):
        report = CheckReport()
        check_vendor_quirks(report)

    assert report.warnings == 0
    assert report.failures == 0


# ---------------------------------------------------------------------------
# check_stale_transitions
# ---------------------------------------------------------------------------


def test_check_stale_transitions_no_file(tmp_path: Path) -> None:
    report = CheckReport()
    check_stale_transitions(report, tmp_path, 10)
    assert report.failures == 0
    assert report.warnings == 0


def test_check_stale_transitions_fresh(tmp_path: Path) -> None:
    pending_file = tmp_path / "pending-transition.json"
    started_at = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)
    ).isoformat()
    pending_file.write_text(json.dumps({"startedAt": started_at}), encoding="utf-8")

    report = CheckReport()
    check_stale_transitions(report, tmp_path, 10)
    assert report.failures == 0
    assert report.warnings == 0


def test_check_stale_transitions_stale(tmp_path: Path) -> None:
    pending_file = tmp_path / "pending-transition.json"
    started_at = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30)
    ).isoformat()
    pending_file.write_text(json.dumps({"startedAt": started_at}), encoding="utf-8")

    report = CheckReport()
    check_stale_transitions(report, tmp_path, 10)
    assert report.failures == 0
    assert report.warnings == 1


def test_check_stale_transitions_invalid_json(tmp_path: Path) -> None:
    pending_file = tmp_path / "pending-transition.json"
    pending_file.write_text("{invalid json", encoding="utf-8")

    report = CheckReport()
    check_stale_transitions(report, tmp_path, 10)
    assert report.failures == 1
    assert report.warnings == 0


def test_check_stale_transitions_missing_field(tmp_path: Path) -> None:
    pending_file = tmp_path / "pending-transition.json"
    pending_file.write_text("{}", encoding="utf-8")

    report = CheckReport()
    check_stale_transitions(report, tmp_path, 10)
    assert report.failures == 1
    assert report.warnings == 0

