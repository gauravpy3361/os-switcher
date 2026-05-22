# Changelog

All notable changes are documented here.

## 0.1.0 - 2026-05-20

- Added Windows to Linux and Linux to Windows one-time boot switching scripts.
- Added config validation, dry-run mode, transition locks, pending state, failure counts, and recovery mode.
- Added target-aware boot-success marking so the wrong OS cannot clear a pending transition as successful.
- Added shared state configuration for production use.
- Added doctor checks, parser helpers, fixtures, Python tests, Bats tests, and Pester tests.
- Added boot-success install, uninstall, and status scripts for Windows Task Scheduler and Linux systemd.
- Added public-release documentation, security policy, contribution guide, and CI workflow.
