# Release Process

## Versioning

Use semantic versioning:

- Patch: docs, tests, or safe bug fixes.
- Minor: new commands or install behavior.
- Major: config format or safety-behavior changes that require migration.

Update:

- `VERSION`
- `CHANGELOG.md`
- README examples when commands change

## Pre-Release Checks

Windows:

```powershell
python .\tools\doctor.py --config .\config.json --platform windows --production --check-writable
Invoke-Pester .\tests\windows_switch.Tests.ps1
```

Linux:

```bash
python3 ./tools/doctor.py --config ./config.json --platform linux --production --check-writable
python3 ./tools/release_check.py
pytest tests
shellcheck linux/*.sh
shfmt -d linux/*.sh tests/linux_switch.bats
bats tests/linux_switch.bats
```

## Physical Hardware Smoke Test

Run on a machine where firmware boot-menu access is confirmed:

1. Confirm Windows and Linux both boot manually.
2. Back up BitLocker or LUKS recovery keys.
3. Run doctor on Windows and Linux.
4. Run dry run on Windows and Linux.
5. Install boot-success automation on Windows and Linux.
6. Switch Windows to Linux once.
7. Confirm Linux marked success.
8. Switch Linux to Windows once.
9. Confirm Windows marked success.
10. Uninstall automation and verify status scripts report it removed.

## Release Artifact

Publish a zip archive containing the repository contents except local config and generated caches. Never include a real `config.json` from a user's machine.
