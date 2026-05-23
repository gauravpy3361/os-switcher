# OS Switcher

One-click dual-boot switching for Windows and Linux using UEFI one-time boot targets.

This is not hot switching or virtualization. It sets the next boot entry, then performs a normal reboot.

Current release: `1.0.0`

## Features

- **Safe:** Performs preflight checks (Python, EFI layout, BitLocker) before touching firmware.
- **Fail-safe:** Backs up EFI entries before every switch. If the boot fails 3 times, it enters Recovery Mode to prevent further automated tampering.
- **Persistent State:** Tracks transitions across reboots using a shared state directory, ensuring the target OS accurately acknowledges a successful boot.
- **Cross-Platform Installers:** Single-script installers for both Windows and Linux, including systemd and Scheduled Task setup for automated boot-success marking.
- **GUI:** Optional, lightweight Python GUI for a simple one-click switch experience.

## First-Time Setup

1. **Clone or Download** the latest release (`os-switcher-x.y.z.zip`) and extract it.

2. **Windows Installation**
   Run an elevated PowerShell session:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\windows\install.ps1
   ```
   This installs OS Switcher to `C:\Program Files\OSSwitcher`, sets up the boot-success Scheduled Task, and creates a Start Menu shortcut.

3. **Linux Installation**
   Run as root:
   ```bash
   sudo bash ./linux/install.sh
   ```
   This installs OS Switcher to `/opt/os-switcher`, sets up the boot-success systemd service, and creates a `/usr/local/bin/os-switcher` symlink.

4. **Configuration**
   On Windows, inspect firmware entries:
   ```powershell
   bcdedit /enum firmware
   ```
   On Linux, inspect EFI entries:
   ```bash
   sudo efibootmgr -v
   ```
   Edit the installed `config.json` (e.g. `C:\Program Files\OSSwitcher\config.json` or `/opt/os-switcher/config.json`) so the Windows-side `targetLabel` matches the Linux firmware application label, and the Linux-side `targetLabel` matches the Windows EFI label. 
   
   *Tip:* For real daily use, set `state.mode` to `shared` and map `state.shared.windowsStateDir` and `state.shared.linuxStateDir` to the same durable storage location accessible from both OSes (e.g. an exFAT or FAT32 partition).

5. **Run the Doctor**
   Verify your setup is healthy before real use:
   ```powershell
   # On Windows
   python "C:\Program Files\OSSwitcher\tools\doctor.py" --config "C:\Program Files\OSSwitcher\config.json"
   ```
   ```bash
   # On Linux
   python3 /opt/os-switcher/tools/doctor.py --config /opt/os-switcher/config.json
   ```

## Daily Use

You can use the **Start Menu shortcut (Windows)** or run `os-switcher` (Linux) to open the GUI. Click the "Switch to ..." button, and it will set the EFI target and reboot.

For command-line users:
```powershell
# Windows
powershell -ExecutionPolicy Bypass -File "C:\Program Files\OSSwitcher\windows\switch-to-linux.ps1" -Reboot
```
```bash
# Linux
sudo /opt/os-switcher/linux/switch-to-windows.sh --reboot
```

## Safety & Recovery Mode

Before any EFI manipulation, OS Switcher automatically backs up your EFI state to your `stateDir` (e.g. `efi-backup-20260520-120000.txt`).

If OS Switcher detects consecutive failed boots (default 3), it will enter **Recovery Mode** and block automated switching.
To view recovery instructions and the location of your newest EFI backup:
```powershell
# Windows
powershell -ExecutionPolicy Bypass -File "C:\Program Files\OSSwitcher\windows\rollback.ps1"
```
```bash
# Linux
sudo /opt/os-switcher/linux/rollback.sh
```

## Uninstallation

To cleanly remove OS Switcher:
```powershell
# Windows (Elevated PowerShell)
powershell -ExecutionPolicy Bypass -File "C:\Program Files\OSSwitcher\windows\uninstall.ps1"
```
```bash
# Linux (root)
sudo bash /opt/os-switcher/linux/uninstall.sh
```
*Note: Uninstallation preserves your state directory in case you need to access your EFI backups or transition history.*

## Important Safety Notes

Read [docs/safety.md](docs/safety.md) before enabling real reboot behavior.
For public or enterprise use, read [docs/enterprise-readiness.md](docs/enterprise-readiness.md) and [docs/release.md](docs/release.md).

## Testing

```bash
# Python tests
pytest
python tools/release_check.py

# Linux script tests
bats tests/linux_switch.bats

# Windows script tests
Invoke-Pester .\tests\windows_switch.Tests.ps1
```

## Validation Ownership

Linux and the GUI use [tools/validate_config.py](tools/validate_config.py). Windows switching keeps a native PowerShell validator inside [windows/switch-to-linux.ps1](windows/switch-to-linux.ps1) so the Windows path does not require Python. When adding config fields, update both validators in the same change.
