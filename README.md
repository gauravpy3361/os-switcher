# OS Switcher

One-click dual-boot switching for Windows and Linux using UEFI one-time boot targets.

This is not hot switching or virtualization. It sets the next boot entry, then performs a normal reboot.

Current release: `0.3.1`

## What This Builds

- Windows -> Linux: PowerShell script sets firmware `bootsequence`, then reboots.
- Linux -> Windows: Bash script sets EFI `BootNext`, then reboots.
- Optional Python GUI: one large button that calls the right script for the current OS.
- Config file: target labels and safety behavior live in one place.
- Persistent transition state: lock files prevent duplicate requests, and pending transitions must be cleared after a successful boot.

## Repository Layout

```text
config.example.json
config.enterprise.example.json
CHANGELOG.md
CONTRIBUTING.md
docs/
  enterprise-readiness.md
  release.md
  setup.md
  safety.md
gui/
  os_switcher_gui.py
linux/
  install-boot-success-service.sh
  mark-boot-success.sh
  status-boot-success-service.sh
  switch-to-windows.sh
  uninstall-boot-success-service.sh
spec/
  os_switcher.tla
tests/
  fixtures/
  linux_switch.bats
  windows_switch.Tests.ps1
tools/
  doctor.py
  make_release.py
  os_switcher_core.py
  validate_config.py
windows/
  install-boot-success-task.ps1
  mark-boot-success.ps1
  status-boot-success-task.ps1
  switch-to-linux.ps1
  uninstall-boot-success-task.ps1
```

## First-Time Setup

Copy the example config:

```powershell
Copy-Item .\config.example.json .\config.json
```

For public/enterprise deployment, start from the shared-state example instead:

```powershell
Copy-Item .\config.enterprise.example.json .\config.json
```

On Windows, inspect firmware entries:

```powershell
bcdedit /enum firmware
```

On Linux, inspect EFI entries:

```bash
sudo efibootmgr -v
```

Update `config.json` so the Windows-side target matches the Linux firmware application label, and the Linux-side target matches the Windows EFI label.

For development, `state.mode` can stay as `local`. For real daily use, set it to `shared` and map `state.shared.windowsStateDir` and `state.shared.linuxStateDir` to the same durable storage location from each OS. This lets the target OS clear the exact pending transition created by the source OS.

Run the doctor in offline mode before touching firmware:

```powershell
python .\tools\doctor.py --config .\config.json --offline
```

For a production-readiness check, use:

```powershell
python .\tools\doctor.py --config .\config.json --production --check-writable --offline
```

On Linux, make the script executable once:

```bash
chmod +x ./linux/*.sh
```

## Dry Run

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\switch-to-linux.ps1 -DryRun
```

Run this from an elevated PowerShell session because Windows may block firmware entry enumeration otherwise.

Linux:

```bash
./linux/switch-to-windows.sh --dry-run
```

## Real Switch

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\switch-to-linux.ps1 -Reboot
```

Linux:

```bash
sudo ./linux/switch-to-windows.sh --reboot
```

## GUI

The GUI is intentionally thin. It delegates to the platform script.

```bash
python gui/os_switcher_gui.py
```

Use the checkbox to allow reboot. Without it, the GUI performs a dry run.

In GUI mode, real reboot requests automatically skip the typed terminal confirmation so the subprocess cannot block waiting for stdin.

## Boot Success Marking

After a successful boot into the target OS, mark that boot as healthy. This clears the pending transition state.

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\mark-boot-success.ps1
```

Linux:

```bash
./linux/mark-boot-success.sh
```

For day-to-day use, wire these into Task Scheduler on Windows and a user or systemd service on Linux.

Install automatic boot-success marking:

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\install-boot-success-task.ps1
```

Linux:

```bash
sudo ./linux/install-boot-success-service.sh
```

Check installation status:

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\status-boot-success-task.ps1
```

Linux:

```bash
./linux/status-boot-success-service.sh
```

Uninstall automatic boot-success marking:

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\uninstall-boot-success-task.ps1
```

Linux:

```bash
sudo ./linux/uninstall-boot-success-service.sh
```

The boot-success scripts are quiet no-ops when there is no pending, failed, or recovery transition state to inspect.

Boot-success marking is target-aware. If Windows boots while the pending target was Linux, Windows records a failed transition instead of clearing it as success. The same applies in reverse on Linux.

Recovery and failure state are not cleared automatically. After you inspect boot health, clear them explicitly:

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\mark-boot-success.ps1 -ClearRecovery
```

Linux:

```bash
./linux/mark-boot-success.sh --clear-recovery
```

## Important Safety Notes

Read [docs/safety.md](docs/safety.md) before enabling real reboot behavior.

For public or enterprise use, read [docs/enterprise-readiness.md](docs/enterprise-readiness.md) and [docs/release.md](docs/release.md).

## Testing

Python tests:

```bash
pytest
python tools/release_check.py
```

Linux script tests:

```bash
bats tests/linux_switch.bats
```

Windows script tests:

```powershell
Invoke-Pester .\tests\windows_switch.Tests.ps1
```

Create a release zip:

```powershell
python .\tools\make_release.py
```

## Validation Ownership

Linux and the GUI use [tools/validate_config.py](tools/validate_config.py). Windows switching keeps a native PowerShell validator inside [windows/switch-to-linux.ps1](windows/switch-to-linux.ps1) so the Windows path does not require Python. The doctor and tests share parser helpers in [tools/os_switcher_core.py](tools/os_switcher_core.py). When adding config fields, update both validators in the same change.
