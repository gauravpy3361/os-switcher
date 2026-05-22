from __future__ import annotations

from pathlib import Path

import pytest

from tools.os_switcher_core import (
    EntryMatchError,
    find_unique_entry,
    parse_linux_efi_entries,
    parse_windows_firmware_entries,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_windows_firmware_entries_and_match_linux_target() -> None:
    entries = parse_windows_firmware_entries((FIXTURES / "bcdedit_firmware.txt").read_text())

    match = find_unique_entry(entries, "linux workspace")

    assert match.identifier == "{11111111-1111-1111-1111-111111111111}"
    assert match.label == "Linux Workspace"


def test_parse_linux_efi_entries_and_match_windows_target() -> None:
    entries = parse_linux_efi_entries((FIXTURES / "efibootmgr.txt").read_text())

    match = find_unique_entry(entries, "Windows Boot Manager")

    assert match.identifier == "0000"
    assert match.label.startswith("Windows Boot Manager")


def test_find_unique_entry_rejects_missing_label() -> None:
    entries = parse_linux_efi_entries((FIXTURES / "efibootmgr.txt").read_text())

    with pytest.raises(EntryMatchError, match="No boot entry matched"):
        find_unique_entry(entries, "Not A Real Entry")


def test_find_unique_entry_rejects_ambiguous_label() -> None:
    entries = parse_linux_efi_entries((FIXTURES / "efibootmgr.txt").read_text())

    with pytest.raises(EntryMatchError, match="Multiple boot entries"):
        find_unique_entry(entries, "w")
