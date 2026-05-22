#!/usr/bin/env python3
"""Shared parsing helpers for OS Switcher tooling and tests."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class BootEntry:
    identifier: str
    label: str
    raw: str


class EntryMatchError(ValueError):
    pass


def parse_windows_firmware_entries(text: str) -> list[BootEntry]:
    entries: list[BootEntry] = []
    current_id = ""
    current_description = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_id, current_description, current_lines
        if current_id:
            entries.append(
                BootEntry(
                    identifier=current_id,
                    label=current_description,
                    raw="\n".join(current_lines).strip(),
                )
            )
        current_id = ""
        current_description = ""
        current_lines = []

    for line in text.splitlines():
        id_match = re.match(r"^\s*identifier\s+(\{[^}]+\})\s*$", line, flags=re.IGNORECASE)
        if id_match:
            flush()
            current_id = id_match.group(1)
            current_lines = [line]
            continue

        if current_id:
            current_lines.append(line)
            description_match = re.match(r"^\s*description\s+(.+?)\s*$", line, flags=re.IGNORECASE)
            if description_match:
                current_description = description_match.group(1).strip()

    flush()
    return entries


def parse_linux_efi_entries(text: str) -> list[BootEntry]:
    entries: list[BootEntry] = []
    for line in text.splitlines():
        match = re.match(r"^Boot([0-9A-Fa-f]{4})\*?\s+(.+?)\s*$", line)
        if match:
            entries.append(BootEntry(identifier=match.group(1).upper(), label=match.group(2), raw=line))
    return entries


def find_unique_entry(entries: list[BootEntry], label: str, *, ignore_case: bool = True) -> BootEntry:
    needle = label.strip()
    if not needle:
        raise EntryMatchError("target label must be a non-empty string")

    if ignore_case:
        needle_for_match = needle.casefold()
        matches = [entry for entry in entries if needle_for_match in entry.label.casefold()]
    else:
        matches = [entry for entry in entries if needle in entry.label]

    if not matches:
        available = "\n".join(f"- {entry.label} {entry.identifier}" for entry in entries)
        raise EntryMatchError(f"No boot entry matched '{label}'. Available entries:\n{available}")

    if len(matches) > 1:
        found = "\n".join(f"- {entry.label} {entry.identifier}" for entry in matches)
        raise EntryMatchError(f"Multiple boot entries matched '{label}'. Make it more specific:\n{found}")

    return matches[0]
