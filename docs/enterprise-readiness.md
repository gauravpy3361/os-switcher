# Enterprise/Public Release Readiness

This project is public-release ready when every item in this gate passes.

## Release Gate

- Config validates on Windows and Linux.
- `state.mode` is `shared` for real daily use.
- `config.enterprise.example.json` has been copied and edited for the target machine.
- The shared state directory is durable, writable by the switch scripts, and not world-writable.
- Windows doctor finds exactly one Linux target firmware entry.
- Linux doctor finds exactly one Windows target EFI entry.
- Dry runs pass on both operating systems.
- Boot-success automation is installed on both operating systems.
- Status scripts report the automation as installed.
- Uninstall scripts are tested.
- Recovery clearing requires an explicit operator command.
- CI checks pass.
- Real reboot test passes in both directions on physical hardware.

## Enterprise Notes

OS Switcher is a workstation tool, not a central fleet-management platform. Enterprise use should wrap it with existing device-management controls:

- Signed release artifacts.
- Restricted write access to `config.json`.
- Documented firmware/boot-manager support matrix.
- Device recovery procedure.
- Change-control approval before changing target labels.
- Backups of BitLocker/LUKS recovery keys.
- A tested path to firmware boot menu access.

## Hardware Validation Matrix

Record every public release against real hardware:

| Area | Required Result |
| --- | --- |
| Windows dry run | Finds exactly one Linux target |
| Linux dry run | Finds exactly one Windows target |
| Windows to Linux | Reboots to Linux without menu interaction |
| Linux success marker | Clears pending transition |
| Linux to Windows | Reboots to Windows without menu interaction |
| Windows success marker | Clears pending transition |
| Wrong-target state | Records failure, does not clear success |
| Recovery mode | Blocks new transitions until explicit clear |
| Uninstall | Removes scheduled task/service cleanly |

## Not Included

These are intentionally out of scope for the first public release:

- Automatic firmware repair.
- Session migration between operating systems.
- Central policy management.
- Remote reboot orchestration.
- Kernel hot switching.
