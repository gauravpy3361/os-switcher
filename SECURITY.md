# Security Policy

OS Switcher changes UEFI one-time boot targets and can reboot the machine. Treat every real switch as a privileged operation.

## Supported Versions

| Version | Supported |
| --- | --- |
| 1.0.x | Yes |

## Reporting A Vulnerability

Do not publish exploit details before maintainers have time to investigate. Report privately through the repository security advisory feature, or by contacting the project maintainer listed on the release page.

Include:

- OS and version
- Firmware type and boot manager
- Exact command run
- Sanitized `config.json`
- Doctor output
- State directory contents, with personal paths redacted

## Security Boundaries

The project does not bypass Secure Boot, disk encryption, firmware passwords, BitLocker, LUKS, TPM policy, or OS login. It only asks firmware to use a configured boot entry on the next reboot.

## Safe Disclosure Expectations

High-risk issues include:

- Real switch bypassing confirmation unexpectedly
- Wrong boot target selected
- Recovery state being cleared incorrectly
- Unsafe handling of paths or config values in privileged scripts
- Installers creating writable privileged files in unsafe locations

Current stable release: v1.0.0
