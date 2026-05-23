#!/usr/bin/env python3
"""Tiny GUI wrapper for the OS Switcher scripts."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from tkinter import BooleanVar, Button, Checkbutton, Label, StringVar, Tk, messagebox


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from validate_config import validate  # noqa: E402


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CONFIG_PATH}. Copy config.example.json to config.json and edit it first."
        )

    validate(CONFIG_PATH)
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def current_platform() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    raise RuntimeError(f"Unsupported platform: {platform.system()}")


def build_command(allow_reboot: bool, force: bool) -> list[str]:
    os_name = current_platform()
    if os_name == "windows":
        script = ROOT / "windows" / "switch-to-linux.ps1"
        command = [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-ConfigPath",
            str(CONFIG_PATH),
        ]
        if allow_reboot:
            command.append("-Reboot")
        else:
            command.append("-DryRun")
        if force or allow_reboot:
            command.append("-Force")
        return command

    script = ROOT / "linux" / "switch-to-windows.sh"
    command = [str(script), "--config", str(CONFIG_PATH)]
    command.append("--reboot" if allow_reboot else "--dry-run")
    if force or allow_reboot:
        command.append("--force")

    if allow_reboot:
        import os
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            if not shutil.which("pkexec"):
                raise RuntimeError(
                    "Polkit ('pkexec') is required for elevated switching on Linux, "
                    "but was not found on this system. Please run OS Switcher from an elevated terminal."
                )
            command = ["pkexec"] + command

    return command


def button_text(config: dict) -> str:
    os_name = current_platform()
    if os_name == "windows":
        return f"Enter {config['windows']['targetLabel']}"
    return f"Return to {config['linux']['targetLabel']}"


def main() -> int:
    try:
        config = load_config()
        label_text = button_text(config)
    except Exception as exc:
        print(f"[os-switcher] ERROR: {exc}", file=sys.stderr)
        messagebox.showerror("OS Switcher", str(exc))
        return 1

    root = Tk()
    root.title("OS Switcher")
    root.geometry("460x220")
    root.resizable(False, False)

    status = StringVar(value="Dry run mode")
    allow_reboot = BooleanVar(value=False)

    def run_switch() -> None:
        switch_button.configure(state="disabled")
        status.set("Running command")
        try:
            command = build_command(allow_reboot.get(), force=False)
            completed = subprocess.run(
                command,
                cwd=str(ROOT),
                check=False,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
            )
            output = "\n".join(
                part for part in [completed.stdout.strip(), completed.stderr.strip()] if part
            )
            if completed.returncode == 0:
                status.set("Command completed")
                messagebox.showinfo("OS Switcher", output or "Command completed.")
            else:
                status.set("Command failed")
                messagebox.showerror("OS Switcher", output or "Command failed.")
        except Exception as exc:
            print(f"[os-switcher] ERROR: {exc}", file=sys.stderr)
            status.set("Command failed")
            messagebox.showerror("OS Switcher", str(exc))
        finally:
            switch_button.configure(state="normal")

    Label(root, text="OS Switcher", font=("Segoe UI", 18, "bold")).pack(pady=(22, 4))
    Label(root, textvariable=status, font=("Segoe UI", 10)).pack(pady=(0, 16))
    switch_button = Button(
        root, text=label_text, font=("Segoe UI", 14), width=28, height=2, command=run_switch
    )
    switch_button.pack()
    Checkbutton(root, text="Allow reboot", variable=allow_reboot).pack(pady=(12, 0))

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
