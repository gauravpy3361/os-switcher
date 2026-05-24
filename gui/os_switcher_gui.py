#!/usr/bin/env python3
"""Tiny GUI wrapper for the OS Switcher scripts."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import BooleanVar, Button, Checkbutton, Frame, Label, StringVar, Tk, messagebox

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
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            if not shutil.which("pkexec"):
                raise RuntimeError(
                    "Polkit ('pkexec') is required for elevated switching on Linux, "
                    "but was not found on this system. Please run OS Switcher from an elevated terminal."
                )
            command = ["pkexec"] + command

    return command


def get_state_dir(config: dict) -> Path:
    os_name = current_platform()
    if config.get("state_mode") == "shared":
        if os_name == "windows":
            return Path(os.path.expandvars(config["windows_effective_state_dir"]))
        return Path(os.path.expandvars(config["linux_effective_state_dir"]))
    if os_name == "windows":
        return Path(os.path.expandvars(config["windows_effective_state_dir"]))
    return Path(os.path.expandvars(config["linux_effective_state_dir"]))


def button_text(config: dict) -> str:
    os_name = current_platform()
    if os_name == "windows":
        return f"Enter {config['windows']['targetLabel']}"
    return f"Return to {config['linux']['targetLabel']}"


def edit_config() -> None:
    if current_platform() == "windows":
        os.startfile(CONFIG_PATH)
    else:
        subprocess.Popen(["xdg-open", str(CONFIG_PATH)])


def get_rollback_command() -> str:
    if current_platform() == "windows":
        return f'powershell -ExecutionPolicy Bypass -File "{ROOT / "windows" / "rollback.ps1"}"'
    return f'sudo bash "{ROOT / "linux" / "rollback.sh"}"'


def main() -> int:
    if platform.system().lower() == "windows":
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            is_admin = False

        if not is_admin:
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                args = sys.argv[1:]
            else:
                args = sys.argv
            
            arg_str = " ".join(f'"{a}"' if " " in a else a for a in args)
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, arg_str, None, 1)
            except Exception as e:
                print(f"[os-switcher] UAC elevation request failed: {e}", file=sys.stderr)
            sys.exit(0)

    try:
        raw_config = load_config()
        config = validate(CONFIG_PATH)
        label_text = button_text(raw_config)
        state_dir = get_state_dir(config)
    except Exception as exc:
        print(f"[os-switcher] ERROR: {exc}", file=sys.stderr)
        root = Tk()
        root.withdraw()
        messagebox.showerror("OS Switcher", str(exc))
        return 1

    root = Tk()
    root.title("OS Switcher")
    root.geometry("480x280")
    root.resizable(False, False)
    
    icon_path = ROOT / "gui" / "os-switcher-logo.ico"
    if icon_path.exists():
        try:
            root.iconbitmap(str(icon_path))
        except Exception as exc:
            print(f"[os-switcher] WARNING: Could not set window icon: {exc}", file=sys.stderr)

    is_recovery = (state_dir / "recovery-mode.json").exists()
    is_pending = (state_dir / "pending-transition.json").exists()
    
    fail_count = 0
    fail_file = state_dir / "boot-fail-count.txt"
    if fail_file.exists():
        try:
            fail_count = int(fail_file.read_text(encoding="utf-8").strip())
        except Exception as exc:
            print(f"[os-switcher] WARNING: Could not read boot fail count: {exc}", file=sys.stderr)

    status = StringVar(value="Dry run mode")
    allow_reboot = BooleanVar(value=False)

    def on_allow_reboot_change(*args: object) -> None:
        if allow_reboot.get():
            status.set("Ready to reboot")
        else:
            status.set("Dry run mode")
            
    allow_reboot.trace_add("write", on_allow_reboot_change)

    def run_switch_thread() -> None:
        try:
            if current_platform() == "windows":
                script_path = ROOT / "windows" / "switch-to-linux.ps1"
                config_path = CONFIG_PATH
                
                cmd_args = [
                    "powershell",
                    "-ExecutionPolicy", "Bypass",
                    "-File", str(script_path),
                    "-ConfigPath", str(config_path),
                ]
                if allow_reboot.get():
                    cmd_args.extend(["-Reboot", "-Force"])
                else:
                    cmd_args.append("-DryRun")
                
                completed = subprocess.run(
                    cmd_args,
                    capture_output=True,
                    text=True,
                    creationflags=0x08000000,  # CREATE_NO_WINDOW
                )
                
                if completed.returncode == 0:
                    if allow_reboot.get():
                        output = "✅ Switching to Linux..."
                    else:
                        output = "✅ Dry run successful — ready to switch!"
                else:
                    err_msg = completed.stdout + completed.stderr
                    err_msg_lower = err_msg.lower()
                    
                    if "no firmware entries" in err_msg_lower or "not found" in err_msg_lower or "could not find" in err_msg_lower:
                        output = "❌ Boot entry not found. Open Edit Config and check your targetLabel matches exactly."
                    elif "config" in err_msg_lower or "invalid" in err_msg_lower or "validation" in err_msg_lower:
                        output = "❌ Config error. Click Edit Config and verify your settings."
                    elif "lock" in err_msg_lower or "transition" in err_msg_lower or "pending" in err_msg_lower:
                        output = "❌ A previous switch is still pending. Restart and try again."
                    elif "bitlocker" in err_msg_lower:
                        output = "❌ BitLocker is active. Go to Control Panel → BitLocker → Turn Off BitLocker."
                    elif "timeout" in err_msg_lower or "reboot" in err_msg_lower:
                        output = "❌ Reboot failed. Try switching manually from PowerShell."
                    elif "administrator" in err_msg_lower:
                        output = "❌ Please run as Administrator."
                    else:
                        output = "❌ Something went wrong. Run doctor.py for details."
            else:
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
            
            def on_complete() -> None:
                if completed.returncode == 0:
                    status_label.configure(fg="#137333")  # Green
                    details.set("")
                    if current_platform() == "windows":
                        status.set(output)
                        messagebox.showinfo("OS Switcher", output)
                    else:
                        status.set("Command completed")
                        messagebox.showinfo("OS Switcher", output or "Command completed.")
                else:
                    status_label.configure(fg="#b31412")  # Red
                    if current_platform() == "windows":
                        status.set(output)
                        details.set("For full details run: python tools\\doctor.py")
                        messagebox.showerror("OS Switcher", output)
                    else:
                        status.set("Command failed")
                        details.set("For full details run: python tools\\doctor.py")
                        messagebox.showerror("OS Switcher", output or "Command failed.")
                switch_button.configure(state="normal")
                
            root.after(0, on_complete)
        except Exception as exc:
            print(f"[os-switcher] ERROR: {exc}", file=sys.stderr)
            def on_error() -> None:
                status_label.configure(fg="#b31412")  # Red
                status.set(f"❌ {exc}")
                details.set("For full details run: python tools\\doctor.py")
                messagebox.showerror("OS Switcher", f"❌ {exc}")
                switch_button.configure(state="normal")
            root.after(0, on_error)

    def run_switch() -> None:
        switch_button.configure(state="disabled")
        status.set("Running command...")
        threading.Thread(target=run_switch_thread, daemon=True).start()

    Label(root, text="OS Switcher", font=("Segoe UI", 18, "bold")).pack(pady=(16, 4))

    status_text = ""
    status_color = "black"
    if is_recovery:
        status_text = "RECOVERY MODE ACTIVE"
        status_color = "red"
    elif is_pending:
        status_text = "Pending transition in progress"
        status_color = "orange"
    elif fail_count > 0:
        status_text = f"Boot failure count: {fail_count}"
        status_color = "orange"
    else:
        status_text = "System health normal"
        status_color = "green"

    Label(root, text=status_text, fg=status_color, font=("Segoe UI", 10, "bold")).pack(pady=(0, 10))

    if is_recovery:
        def show_rollback() -> None:
            messagebox.showinfo(
                "Rollback Instructions",
                "Automated switching is blocked due to consecutive boot failures.\n\n"
                f"Please run the rollback script in a terminal:\n\n{get_rollback_command()}"
            )
        Button(root, text="View Rollback Instructions", fg="red", command=show_rollback).pack(pady=(0, 10))
        switch_button = Button(
            root, text=label_text, font=("Segoe UI", 14), width=28, height=2, state="disabled"
        )
    else:
        switch_button = Button(
            root, text=label_text, font=("Segoe UI", 14), width=28, height=2, command=run_switch
        )

    switch_button.pack()

    bottom_frame = Frame(root)
    bottom_frame.pack(pady=(12, 0))
    Checkbutton(bottom_frame, text="Allow reboot", variable=allow_reboot).pack(side="left", padx=(0, 20))
    Button(bottom_frame, text="Edit Config", command=edit_config).pack(side="left")

    status_label = Label(root, textvariable=status, font=("Segoe UI", 9), fg="gray")
    status_label.pack(pady=(10, 0))

    details = StringVar(value="")
    details_label = Label(root, textvariable=details, font=("Segoe UI", 8), fg="gray")
    details_label.pack(pady=(2, 0))

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
