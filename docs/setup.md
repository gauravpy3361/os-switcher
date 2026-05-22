# Setup

## Windows

Open an elevated PowerShell window.

List firmware entries:

```powershell
bcdedit /enum firmware
```

Find the entry that boots Linux. Put part of its `description` into `config.json`:

```json
{
  "windows": {
    "targetLabel": "Linux Workspace"
  }
}
```

Dry run:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\switch-to-linux.ps1 -DryRun
```

Offline doctor check:

```powershell
python .\tools\doctor.py --config .\config.json --platform windows --offline
```

Real switch:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\switch-to-linux.ps1 -Reboot
```

Mark a successful Windows boot:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\mark-boot-success.ps1
```

Install automatic Windows boot-success marking:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\install-boot-success-task.ps1
```

Check or remove the Windows boot-success task:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\status-boot-success-task.ps1
powershell -ExecutionPolicy Bypass -File .\windows\uninstall-boot-success-task.ps1
```

## Linux

Install `efibootmgr` if needed.

List EFI entries:

```bash
sudo efibootmgr -v
```

Find the entry that boots Windows. Put part of its label into `config.json`:

```json
{
  "linux": {
    "targetLabel": "Windows Boot Manager"
  }
}
```

Dry run:

```bash
chmod +x ./linux/*.sh
./linux/switch-to-windows.sh --dry-run
```

Offline doctor check:

```bash
python3 ./tools/doctor.py --config ./config.json --platform linux --offline
```

Real switch:

```bash
sudo ./linux/switch-to-windows.sh --reboot
```

Mark a successful Linux boot:

```bash
./linux/mark-boot-success.sh
```

Install automatic Linux boot-success marking:

```bash
sudo ./linux/install-boot-success-service.sh
```

Check or remove the Linux boot-success service:

```bash
./linux/status-boot-success-service.sh
sudo ./linux/uninstall-boot-success-service.sh
```

## Shared State For Real Use

Keep `state.mode` as `local` while learning and running tests. Before day-to-day real switching, configure `state.mode` as `shared` and make both paths point to the same durable storage location:

```json
{
  "state": {
    "mode": "shared",
    "shared": {
      "windowsStateDir": "D:\\OSSwitcherState",
      "linuxStateDir": "/mnt/os-switcher-state"
    }
  }
}
```

Run the production doctor check after editing:

```bash
python3 ./tools/doctor.py --config ./config.json --production --check-writable --offline
```
