# Changelog

All notable changes are documented here.

## [1.1.0] - 2026-05-23
### Added
- windows/OSSwitcher-Setup.iss: Professional Inno Setup Windows installer
- tools/build_installer.py: Build script for Windows .exe installer
- linux/build-appimage.sh: Linux AppImage builder for single-file distribution
- tools/setup_wizard.py: Elevation check (clear error if not admin/root)

## [1.0.0] - 2026-05-23
### Added
- Setup wizard for guided EFI configuration
- GUI UX polish: threading, status display, recovery mode indicator
- Uninstallers for Windows and Linux
- Centralized file logging to state_dir/os-switcher.log
- Non-English locale support for BitLocker detection (CIM-based)
- wmic replaced with Get-CimInstance for vendor quirk detection
- Stage 8 hardening: stale transition detection (--check-stale flag)
- Power failure edge case documented in docs/safety.md
- Full test coverage for efi_backup.py, doctor.py, rollback scripts
### Fixed
- GitHub Actions CI: all 3 jobs now passing cleanly
- shellcheck SC2012 warning in rollback.sh
- EM dash encoding issue in rollback.ps1 (PowerShell 5.1 compatibility)
- Test mock tuple fix for check_python_version test

## [0.4.0] - 2026-05-23
### Added
- linux/uninstall.sh: Full Linux uninstaller — removes install dir, symlink, and systemd service; preserves state directory
- windows/uninstall.ps1: Full Windows uninstaller — removes install dir, Start Menu shortcut, and scheduled task; preserves state directory
### Fixed
- VERSION file now tracks git tag correctly (v0.3.2)
- tools/doctor.py: sys.path fix so script runs from project root
- tools/doctor.py: manage-bde absence now reports WARN not OK
- tools/efi_backup.py: --restore crash on missing path argument
- windows/switch-to-linux.ps1: manage-bde wrapped in try/catch for Windows Home
- windows/switch-to-linux.ps1: config validation now enforces maxBootFailures >= 1 and rebootTimeoutSeconds >= 0
- windows/install.ps1: suppressed duplicate boot-task output
- windows/install-boot-success-task.ps1: task now fires only for installing user at RunLevel Limited
- linux/install.sh: added rsync availability check; chmod all 6 linux scripts
- tools/make_release.py: tests/ now excluded from release zip
- tools/release_check.py: added 5 missing files to REQUIRED_FILES
- README.md: corrected stale version number
- CHANGELOG.md: backfilled missing v0.2.0 and v0.3.0 entries

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
