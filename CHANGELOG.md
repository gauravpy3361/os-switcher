# Changelog

All notable changes are documented here.

## [0.3.1] - 2026-05-23
### Added
- linux/install.sh: Single-script Linux installer with preflight checks
- windows/install.ps1: Single-script Windows installer with preflight checks
- tools/efi_backup.py: EFI backup utility (runs before every switch)
- linux/rollback.sh: Recovery mode diagnostics and manual restore guide
- windows/rollback.ps1: Recovery mode diagnostics and manual restore guide

## [0.3.0] - 2026-05-23
### Added
- linux/rollback.sh: Recovery mode diagnostics and manual restore guide
- windows/rollback.ps1: Recovery mode diagnostics and manual restore guide
- tools/efi_backup.py: EFI backup utility, runs automatically before every switch

## [0.2.0] - 2026-05-23
### Added
- tools/doctor.py: Python version, EFI layout, GRUB timeout, BitLocker, vendor quirk checks
- windows/switch-to-linux.ps1: Hard BitLocker block before switching
- linux/install.sh: Single-script Linux installer with preflight checks
- windows/install.ps1: Single-script Windows installer with preflight checks

## [0.1.1] - 2026-05-23
### Fixed
- linux/switch-to-windows.sh: Lock erasure concurrency bug (PID-based ownership check)
- linux/switch-to-windows.sh: Reboot failure state leak on systemctl reboot failure
- linux/switch-to-windows.sh: Unprotected JSON parsers in embedded Python blocks
- windows/switch-to-linux.ps1: Reboot failure state leak on shutdown command failure
- windows/switch-to-linux.ps1: Lock collision detail loss (now shows real exception)
- windows/switch-to-linux.ps1: Unprotected JSON and fail-count parsers
- gui/os_switcher_gui.py: Exceptions now logged to stderr before messagebox display

## 0.1.0 - 2026-05-20

- Added Windows to Linux and Linux to Windows one-time boot switching scripts.
- Added config validation, dry-run mode, transition locks, pending state, failure counts, and recovery mode.
- Added target-aware boot-success marking so the wrong OS cannot clear a pending transition as successful.
- Added shared state configuration for production use.
- Added doctor checks, parser helpers, fixtures, Python tests, Bats tests, and Pester tests.
- Added boot-success install, uninstall, and status scripts for Windows Task Scheduler and Linux systemd.
- Added public-release documentation, security policy, contribution guide, and CI workflow.
