#!/usr/bin/env python3
"""Interactive GUI and terminal setup wizard for OS Switcher."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tkinter
from pathlib import Path

# Add tools to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from os_switcher_core import (
    BootEntry,
    parse_linux_efi_entries,
    parse_windows_firmware_entries,
)


def current_platform() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    return system


def detect_efi_entries(os_name: str) -> list[BootEntry]:
    if os_name == "windows":
        try:
            completed = subprocess.run(
                ["bcdedit", "/enum", "firmware"],
                capture_output=True,
                text=True,
                check=False,
            )
            # bcdedit returns a non-zero exit code if not running as administrator
            if completed.returncode != 0:
                print(f"Error: bcdedit command failed (exit code {completed.returncode}).", file=sys.stderr)
                print(f"Error details: {completed.stderr.strip()}", file=sys.stderr)
                sys.exit(1)
            entries = parse_windows_firmware_entries(completed.stdout)
            return entries
        except Exception as exc:
            print(f"Error: Failed to execute bcdedit: {exc}", file=sys.stderr)
            sys.exit(1)
    elif os_name == "linux":
        try:
            completed = subprocess.run(
                ["efibootmgr", "-v"],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                print(f"Error: efibootmgr command failed (exit code {completed.returncode}).", file=sys.stderr)
                print(f"Error details: {completed.stderr.strip()}", file=sys.stderr)
                sys.exit(1)
            entries = parse_linux_efi_entries(completed.stdout)
            return entries
        except Exception as exc:
            print(f"Error: Failed to execute efibootmgr: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error: Unsupported operating system platform '{os_name}'.", file=sys.stderr)
        sys.exit(1)


def is_gui_available() -> bool:
    try:
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


class ScrollableFrame(tkinter.Frame):
    def __init__(self, parent, bg_color):
        super().__init__(parent, bg=bg_color)

        self.canvas = tkinter.Canvas(self, bg=bg_color, highlightthickness=0)
        self.scrollbar = tkinter.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tkinter.Frame(self.canvas, bg=bg_color)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")


class SetupWizardApp:
    def __init__(self, output_path: Path, dry_run: bool):
        self.output_path = output_path
        self.dry_run = dry_run

        self.root = tkinter.Tk()
        self.root.title("OS Switcher Setup")
        self.root.geometry("540x390")
        self.root.resizable(False, False)

        icon_path = ROOT / "gui" / "os-switcher-logo.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Premium Modern Colors
        self.bg_color = "#ffffff"
        self.primary_color = "#1a73e8"      # Premium Google Blue
        self.primary_hover = "#1557b0"
        self.text_color = "#202124"
        self.sec_text_color = "#5f6368"
        self.border_color = "#dadce0"

        self.root.configure(bg=self.bg_color)

        self.os_name = current_platform()
        self.entries: list[BootEntry] = []
        self.windows_entry: BootEntry | None = None
        self.linux_entry: BootEntry | None = None
        self.state_dir = "C:\\ProgramData\\OSSwitcher" if self.os_name == "windows" else "/var/lib/os-switcher"

        self.container = tkinter.Frame(self.root, bg=self.bg_color)
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        self.show_welcome_screen()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_welcome_screen(self):
        self.clear_container()

        # Spacer
        tkinter.Label(self.container, text="", bg=self.bg_color, height=2).pack()

        # Title
        lbl_title = tkinter.Label(
            self.container,
            text="Welcome to OS Switcher",
            font=("Arial", 22, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        lbl_title.pack(pady=10)

        # Subtitle
        lbl_sub = tkinter.Label(
            self.container,
            text="Let's detect your boot entries and configure the switcher.",
            font=("Arial", 12),
            fg=self.sec_text_color,
            bg=self.bg_color,
            wraplength=480
        )
        lbl_sub.pack(pady=10)

        # Spacer
        tkinter.Label(self.container, text="", bg=self.bg_color, height=2).pack()

        # Button
        btn_start = tkinter.Button(
            self.container,
            text="Get Started",
            font=("Arial", 11, "bold"),
            bg=self.primary_color,
            fg="#ffffff",
            activebackground=self.primary_hover,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.show_detecting_screen
        )
        btn_start.pack()

    def show_detecting_screen(self):
        self.clear_container()

        tkinter.Label(self.container, text="", bg=self.bg_color, height=3).pack()

        lbl_status = tkinter.Label(
            self.container,
            text="Detecting your boot entries...",
            font=("Arial", 14, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        lbl_status.pack(pady=10)

        lbl_detail = tkinter.Label(
            self.container,
            text="Reading UEFI configuration from firmware...",
            font=("Arial", 10),
            fg=self.sec_text_color,
            bg=self.bg_color
        )
        lbl_detail.pack(pady=5)

        # Background thread to run detection
        import threading

        def do_detect():
            try:
                # We can reuse detect_efi_entries but let's capture SystemExit if it fails
                detected = detect_efi_entries(self.os_name)
                # Filter empty and truncate labels
                self.entries = []
                for e in detected:
                    cleaned_label = e.label.split('\t')[0].strip()
                    if cleaned_label:
                        self.entries.append(BootEntry(identifier=e.identifier, label=cleaned_label, raw=e.raw))

                if not self.entries:
                    self.root.after(0, lambda: self.show_error("No boot entries could be parsed from the firmware."))
                else:
                    self.root.after(0, self.show_pick_windows_screen)
            except SystemExit:
                self.root.after(0, lambda: self.show_error("Failed to detect EFI entries. Ensure you are running with elevation (Administrator/root)."))
            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"Error during detection: {e}"))

        threading.Thread(target=do_detect, daemon=True).start()

    def show_error(self, message: str):
        self.clear_container()

        tkinter.Label(self.container, text="", bg=self.bg_color, height=2).pack()

        lbl_err = tkinter.Label(
            self.container,
            text="An Error Occurred",
            font=("Arial", 16, "bold"),
            fg="#d93025",
            bg=self.bg_color
        )
        lbl_err.pack(pady=10)

        lbl_msg = tkinter.Label(
            self.container,
            text=message,
            font=("Arial", 11),
            fg=self.text_color,
            bg=self.bg_color,
            wraplength=480
        )
        lbl_msg.pack(pady=10)

        tkinter.Label(self.container, text="", bg=self.bg_color, height=2).pack()

        btn_exit = tkinter.Button(
            self.container,
            text="Exit",
            font=("Arial", 11, "bold"),
            bg="#d93025",
            fg="#ffffff",
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.root.destroy
        )
        btn_exit.pack()

    def show_pick_windows_screen(self):
        self.clear_container()

        lbl_title = tkinter.Label(
            self.container,
            text="Which entry is Windows?",
            font=("Arial", 14, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        lbl_title.pack(anchor="w", pady=10)

        # Scrollable container for the entries
        scroll_frame = ScrollableFrame(self.container, self.bg_color)
        scroll_frame.pack(fill="both", expand=True, pady=10)

        for entry in self.entries:
            btn = tkinter.Button(
                scroll_frame.scrollable_frame,
                text=f"{entry.label} (ID: {entry.identifier})",
                font=("Arial", 10),
                bg="#f1f3f4",
                fg=self.text_color,
                activebackground=self.primary_color,
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                anchor="w",
                padx=15,
                pady=10,
                cursor="hand2",
                width=50
            )
            btn.configure(command=lambda e=entry: self.select_windows_entry(e))
            btn.pack(fill="x", pady=4)

    def select_windows_entry(self, entry: BootEntry):
        self.windows_entry = entry
        self.show_pick_linux_screen()

    def show_pick_linux_screen(self):
        self.clear_container()

        lbl_title = tkinter.Label(
            self.container,
            text="Which entry is Linux?",
            font=("Arial", 14, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        lbl_title.pack(anchor="w", pady=10)

        scroll_frame = ScrollableFrame(self.container, self.bg_color)
        scroll_frame.pack(fill="both", expand=True, pady=10)

        for entry in self.entries:
            if self.windows_entry and entry.identifier == self.windows_entry.identifier:
                continue

            btn = tkinter.Button(
                scroll_frame.scrollable_frame,
                text=f"{entry.label} (ID: {entry.identifier})",
                font=("Arial", 10),
                bg="#f1f3f4",
                fg=self.text_color,
                activebackground=self.primary_color,
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                anchor="w",
                padx=15,
                pady=10,
                cursor="hand2",
                width=50
            )
            btn.configure(command=lambda e=entry: self.select_linux_entry(e))
            btn.pack(fill="x", pady=4)

    def select_linux_entry(self, entry: BootEntry):
        self.linux_entry = entry
        self.show_confirm_screen()

    def show_confirm_screen(self):
        self.clear_container()

        lbl_title = tkinter.Label(
            self.container,
            text="Configuration Summary",
            font=("Arial", 14, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        lbl_title.pack(anchor="w", pady=10)

        # Summary Box Frame
        summary_frame = tkinter.Frame(self.container, bg="#f8f9fa", bd=1, relief="solid")
        summary_frame.pack(fill="x", pady=15, ipady=10)

        # Inner labels
        tkinter.Label(
            summary_frame,
            text=f"Windows Entry: {self.windows_entry.label} ({self.windows_entry.identifier})",
            font=("Arial", 11),
            fg=self.text_color,
            bg="#f8f9fa",
            anchor="w",
            padx=15
        ).pack(fill="x", pady=4)

        tkinter.Label(
            summary_frame,
            text=f"Linux Entry:   {self.linux_entry.label} ({self.linux_entry.identifier})",
            font=("Arial", 11),
            fg=self.text_color,
            bg="#f8f9fa",
            anchor="w",
            padx=15
        ).pack(fill="x", pady=4)

        # Cross platform State directory summary
        linux_state = "/var/lib/os-switcher"
        win_state = "C:\\ProgramData\\OSSwitcher"
        effective_state = win_state if self.os_name == "windows" else linux_state

        tkinter.Label(
            summary_frame,
            text=f"State Directory (Local): {effective_state}",
            font=("Arial", 10),
            fg=self.sec_text_color,
            bg="#f8f9fa",
            anchor="w",
            padx=15
        ).pack(fill="x", pady=4)

        # Buttons Row Frame
        btn_frame = tkinter.Frame(self.container, bg=self.bg_color)
        btn_frame.pack(fill="x", pady=15)

        btn_back = tkinter.Button(
            btn_frame,
            text="Back",
            font=("Arial", 11, "bold"),
            bg="#f1f3f4",
            fg=self.text_color,
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.show_pick_windows_screen
        )
        btn_back.pack(side="left")

        btn_install = tkinter.Button(
            btn_frame,
            text="Install Configuration",
            font=("Arial", 11, "bold"),
            bg=self.primary_color,
            fg="#ffffff",
            activebackground=self.primary_hover,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.install_configuration
        )
        btn_install.pack(side="right")

    def install_configuration(self):
        example_path = ROOT / "config.example.json"
        if not example_path.exists():
            self.show_error(f"Template config.example.json not found at {example_path}.")
            return

        try:
            with open(example_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as exc:
            self.show_error(f"Failed to read template config.example.json: {exc}")
            return

        config_data["windows"]["bootEntryLabel"] = self.windows_entry.label
        config_data["linux"]["bootEntryLabel"] = self.linux_entry.label
        config_data["windows"]["targetLabel"] = self.linux_entry.label
        config_data["linux"]["targetLabel"] = self.windows_entry.label

        if self.os_name == "windows":
            config_data["windows"]["stateDir"] = self.state_dir
            config_data["linux"]["stateDir"] = "/var/lib/os-switcher"
        else:
            config_data["linux"]["stateDir"] = self.state_dir
            config_data["windows"]["stateDir"] = "C:\\ProgramData\\OSSwitcher"

        if self.dry_run:
            self.show_done_screen("Dry run complete. No configuration was written.")
        else:
            try:
                with open(self.output_path, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, indent=2)
                    f.write("\n")
                self.show_done_screen("config.json written successfully.")
            except Exception as exc:
                self.show_error(f"Failed to write configuration: {exc}")

    def show_done_screen(self, status_msg: str):
        self.clear_container()

        lbl_title = tkinter.Label(
            self.container,
            text="You're all set!",
            font=("Arial", 16, "bold"),
            fg=self.primary_color,
            bg=self.bg_color
        )
        lbl_title.pack(anchor="w", pady=5)

        lbl_status = tkinter.Label(
            self.container,
            text=status_msg,
            font=("Arial", 10),
            fg=self.sec_text_color,
            bg=self.bg_color
        )
        lbl_status.pack(anchor="w", pady=2)

        lbl_doc = tkinter.Label(
            self.container,
            text="Running doctor checks...",
            font=("Arial", 11, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        lbl_doc.pack(anchor="w", pady=10)

        # TextBox/Label for Doctor output
        doc_frame = tkinter.Frame(self.container, bg="#f8f9fa", bd=1, relief="solid")
        doc_frame.pack(fill="both", expand=True, pady=5)

        doc_text = tkinter.Text(doc_frame, font=("Courier", 9), bg="#f8f9fa", fg=self.text_color, wrap="word", bd=0, highlightthickness=0)
        doc_scroll = tkinter.Scrollbar(doc_frame, command=doc_text.yview)
        doc_text.configure(yscrollcommand=doc_scroll.set)

        doc_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        doc_scroll.pack(side="right", fill="y")

        import threading

        def run_doctor():
            doctor_path = ROOT / "tools" / "doctor.py"
            try:
                completed = subprocess.run(
                    [sys.executable, str(doctor_path), "--config", str(self.output_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                output = completed.stdout + completed.stderr

                status_lbl_text = "Doctor validation complete."
                fg_status = self.text_color
                if completed.returncode == 0:
                    status_lbl_text = "Doctor validation: SUCCESS (all checks passed)"
                    fg_status = "#137333"
                else:
                    status_lbl_text = "Doctor validation: WARNING/FAIL (check details)"
                    fg_status = "#b31412"

                def update_ui():
                    doc_text.insert("end", output)
                    doc_text.configure(state="disabled")
                    lbl_doc.configure(text=status_lbl_text, fg=fg_status)

                self.root.after(0, update_ui)
            except Exception as e:
                def update_ui_err():
                    doc_text.insert("end", f"Failed to run doctor check: {e}")
                    doc_text.configure(state="disabled")
                    lbl_doc.configure(text="Doctor run failed.", fg="#d93025")
                self.root.after(0, update_ui_err)

        threading.Thread(target=run_doctor, daemon=True).start()

        # Final Launch Button
        btn_close = tkinter.Button(
            self.container,
            text="Launch OS Switcher",
            font=("Arial", 11, "bold"),
            bg=self.primary_color,
            fg="#ffffff",
            activebackground=self.primary_hover,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.launch_os_switcher
        )
        btn_close.pack(anchor="e", pady=10)

    def launch_os_switcher(self):
        self.root.destroy()
        gui_path = ROOT / "gui" / "os_switcher_gui.py"
        try:
            subprocess.Popen([sys.executable, str(gui_path)])
        except Exception as e:
            print(f"Error launching OS Switcher GUI: {e}", file=sys.stderr)


def run_terminal_wizard(output_path: Path, dry_run: bool) -> int:
    os_name = current_platform()

    # STEP 2 — Detect EFI entries
    print("Detecting EFI boot entries...")
    detected_entries = detect_efi_entries(os_name)

    entries = []
    for e in detected_entries:
        cleaned_label = e.label.split('\t')[0].strip()
        if cleaned_label:
            entries.append(BootEntry(identifier=e.identifier, label=cleaned_label, raw=e.raw))

    if not entries:
        print("Error: No boot entries could be parsed from the firmware output.", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully detected {len(entries)} boot entry/entries.\n")

    # STEP 3 — Show entries to user
    print("Detected Boot Entries:")
    for idx, entry in enumerate(entries, start=1):
        print(f"  [{idx}] {entry.label} (ID: {entry.identifier})")
    print("")

    # STEP 4 — Ask user to pick Windows entry
    while True:
        try:
            windows_input = input("Enter the number for your WINDOWS boot entry: ").strip()
            win_idx = int(windows_input)
            if 1 <= win_idx <= len(entries):
                windows_entry = entries[win_idx - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(entries)}.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # STEP 5 — Ask user to pick Linux entry
    while True:
        try:
            linux_input = input("Enter the number for your LINUX boot entry: ").strip()
            lin_idx = int(linux_input)
            if 1 <= lin_idx <= len(entries):
                if lin_idx == win_idx:
                    print("Error: The Linux boot entry must be different from the Windows boot entry.")
                    continue
                linux_entry = entries[lin_idx - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(entries)}.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    print("")

    # STEP 6 — Ask for state directory
    default_state_dir = "C:\\ProgramData\\OSSwitcher" if os_name == "windows" else "/var/lib/os-switcher"
    state_dir = default_state_dir

    print("")

    # STEP 7 — Show summary and confirm
    print("Configuration Summary:")
    print(f"  Windows entry: {windows_entry.label} ({windows_entry.identifier})")
    print(f"  Linux entry: {linux_entry.label} ({linux_entry.identifier})")
    print(f"  State directory: {state_dir}")
    print("")

    while True:
        confirm = input("Write config.json? (yes/no): ").strip().lower()
        if confirm in ("yes", "y"):
            break
        elif confirm in ("no", "n"):
            print("Setup cancelled by user. Exiting.")
            return 0
        else:
            print("Please enter 'yes' or 'no'.")

    # STEP 8 — Write config.json
    example_path = ROOT / "config.example.json"
    if not example_path.exists():
        print(f"Error: Template config.example.json not found at {example_path}.", file=sys.stderr)
        return 1

    try:
        with open(example_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as exc:
        print(f"Error: Failed to read template config.example.json: {exc}", file=sys.stderr)
        return 1

    # Fill in template
    config_data["windows"]["bootEntryLabel"] = windows_entry.label
    config_data["linux"]["bootEntryLabel"] = linux_entry.label
    config_data["windows"]["targetLabel"] = linux_entry.label
    config_data["linux"]["targetLabel"] = windows_entry.label

    if os_name == "windows":
        config_data["windows"]["stateDir"] = state_dir
        config_data["linux"]["stateDir"] = "/var/lib/os-switcher"
    else:
        config_data["linux"]["stateDir"] = state_dir
        config_data["windows"]["stateDir"] = "C:\\ProgramData\\OSSwitcher"

    # Handle dry run or writing
    if dry_run:
        print("\n[DRY RUN] Would write following config.json content to:", output_path)
        print(json.dumps(config_data, indent=2))
        print("[DRY RUN] Dry run finished. No file was written.")
        return 0
    else:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
                f.write("\n")
            print(f"\nconfig.json written successfully. You are ready to switch!")
        except Exception as exc:
            print(f"Error: Failed to write configuration to {output_path}: {exc}", file=sys.stderr)
            return 1

    # STEP 9 — Run doctor check
    print("\nRunning doctor check to verify configuration...")
    doctor_path = ROOT / "tools" / "doctor.py"
    try:
        completed = subprocess.run(
            [sys.executable, str(doctor_path), "--config", str(output_path)],
            check=False,
            text=True,
        )
    except Exception as exc:
        print(f"Error: Failed to run doctor check: {exc}", file=sys.stderr)
        return 1

    return completed.returncode


def main() -> int:
    os_name = current_platform()
    if os_name == "windows":
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            is_admin = False
        if not is_admin:
            print("ERROR: This wizard must be run as Administrator.", file=sys.stderr)
            print("Right-click PowerShell and select 'Run as Administrator', then try again.", file=sys.stderr)
            sys.exit(1)
    elif os_name == "linux":
        try:
            import os
            is_root = os.geteuid() == 0
        except Exception:
            is_root = False
        if not is_root:
            print("ERROR: This wizard must be run as root.", file=sys.stderr)
            print("Run: sudo python3 tools/setup_wizard.py", file=sys.stderr)
            sys.exit(1)

    parser = argparse.ArgumentParser(description="OS Switcher Setup Wizard")
    parser.add_argument("-o", "--output", type=Path, help="Path to write the config.json file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be written without writing it")
    args = parser.parse_args()

    config_output_path = args.output if args.output else (ROOT / "config.json")

    # STEP 1 — Welcome banner
    print("==========================================")
    print("OS Switcher Setup Wizard v1.0.0")
    print("This wizard will detect your boot entries and create config.json")
    print("==========================================\n")

    if is_gui_available():
        app = SetupWizardApp(config_output_path, args.dry_run)
        app.root.mainloop()
        return 0
    else:
        print("GUI environment not detected. Falling back to interactive terminal setup wizard.\n")
        return run_terminal_wizard(config_output_path, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
