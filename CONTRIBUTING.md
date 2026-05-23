# Contributing

Thanks for helping make OS Switcher safer.

## Development Setup

Windows:

```powershell
winget install Git.Git
winget install Python.Python.3.12
Install-Module Pester -Scope CurrentUser -Force -SkipPublisherCheck
```

Ubuntu or WSL:

```bash
sudo apt update
sudo apt install -y shellcheck shfmt bats python3 python3-pytest
```

## Required Checks

Run from the repository root:

```bash
pytest tests
shellcheck linux/*.sh
shfmt -d linux/*.sh tests/linux_switch.bats
bats tests/linux_switch.bats
```

On Windows:

```powershell
Invoke-Pester .\tests\windows_switch.Tests.ps1
```

## Boot-Safety Rules

- Keep dry-run support for every new operation that would touch firmware.
- Do not combine fixture/mock firmware output with real reboot behavior.
- Do not clear recovery state automatically.
- Do not add dependencies to the Windows switch path unless there is no native option.
- Update both `tools/validate_config.py` and `windows/switch-to-linux.ps1` when config fields change.
- Add tests for any parser, state, install, or recovery behavior change.

## Pull Request Checklist

- Tests pass on Windows and Linux.
- Docs explain any new privileged behavior.
- The doctor command catches new setup requirements.
- Real reboot behavior remains opt-in.
- `CHANGELOG.md` is updated for user-visible changes.

This project follows semantic versioning. Current stable: v1.0.0
