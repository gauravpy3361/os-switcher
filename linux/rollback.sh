#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="$SCRIPT_DIR/../config.json"

while [[ $# -gt 0 ]]; do
	case "$1" in
	--config)
		CONFIG_PATH="$2"
		shift 2
		;;
	*)
		echo "Unknown argument: $1" >&2
		exit 2
		;;
	esac
done

if [[ ! -f "$CONFIG_PATH" ]]; then
	echo "Config file not found: $CONFIG_PATH" >&2
	exit 1
fi

eval "$(python3 "$SCRIPT_DIR/../tools/validate_config.py" "$CONFIG_PATH" --shell)"
STATE_DIR="$LINUX_EFFECTIVE_STATE_DIR"
RECOVERY_PATH="$STATE_DIR/recovery-mode.json"

if [[ ! -f "$RECOVERY_PATH" ]]; then
	echo "No recovery mode active."
	exit 0
fi

echo "=== Current EFI Boot Configuration ==="
if command -v efibootmgr >/dev/null 2>&1; then
	efibootmgr
else
	echo "efibootmgr is not installed or not in PATH."
fi
echo "======================================"

NEWEST_BACKUP="$(find "$STATE_DIR" -maxdepth 1 -name 'efi-backup-*.txt' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n 1 | cut -d' ' -f2- || true)"
if [[ -z "$NEWEST_BACKUP" ]]; then
	NEWEST_BACKUP="No backup files found in $STATE_DIR"
fi

echo ""
echo "RECOVERY MODE ACTIVE — Automatic rollback not possible (EFI manipulation is unsafe)."
echo "Please manually set your boot order using efibootmgr."
echo "Your last EFI backup is at: $NEWEST_BACKUP"
exit 1
