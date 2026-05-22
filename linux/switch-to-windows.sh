#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="$SCRIPT_DIR/../config.json"
EFIBOOTMGR_OUTPUT_PATH=""
DRY_RUN=0
REBOOT=0
FORCE=0

while [[ $# -gt 0 ]]; do
	case "$1" in
	--config)
		CONFIG_PATH="$2"
		shift 2
		;;
	--dry-run)
		DRY_RUN=1
		shift
		;;
	--efibootmgr-output)
		EFIBOOTMGR_OUTPUT_PATH="$2"
		shift 2
		;;
	--reboot)
		REBOOT=1
		shift
		;;
	--force)
		FORCE=1
		shift
		;;
	*)
		echo "Unknown argument: $1" >&2
		exit 2
		;;
	esac
done

if [[ -n "$EFIBOOTMGR_OUTPUT_PATH" && "$REBOOT" == "1" ]]; then
	echo "--efibootmgr-output is for dry-run/testing only and cannot be combined with --reboot." >&2
	exit 2
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
	echo "Config file not found: $CONFIG_PATH. Copy config.example.json to config.json and edit it first." >&2
	exit 1
fi

if [[ -z "$EFIBOOTMGR_OUTPUT_PATH" ]] && ! command -v efibootmgr >/dev/null 2>&1; then
	echo "efibootmgr is required. Install it with your distro package manager." >&2
	exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
	echo "python3 is required to read config.json." >&2
	exit 1
fi

eval "$(python3 "$SCRIPT_DIR/../tools/validate_config.py" "$CONFIG_PATH" --shell)"

TARGET_LABEL="$LINUX_TARGET_LABEL"
REBOOT_DELAY="$LINUX_REBOOT_DELAY_SECONDS"
CONFIG_REQUIRE_CONFIRMATION="$REQUIRE_CONFIRMATION"
STATE_DIR="$LINUX_EFFECTIVE_STATE_DIR"
PENDING_TIMEOUT_MINUTES="$PENDING_TRANSITION_TIMEOUT_MINUTES"
CONFIG_MAX_BOOT_FAILURES="$MAX_BOOT_FAILURES"

if [[ -z "$TARGET_LABEL" ]]; then
	echo "linux.targetLabel is required in config." >&2
	exit 1
fi

mkdir -p "$STATE_DIR"
LOCK_DIR="$STATE_DIR/transition.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
	echo "Another OS Switcher transition appears to be running. Lock path: $LOCK_DIR" >&2
	exit 1
fi

cleanup_lock() {
	rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup_lock EXIT

PENDING_PATH="$STATE_DIR/pending-transition.json"
STAGED_PATH="$STATE_DIR/transition-staged.json"
FAIL_COUNT_PATH="$STATE_DIR/boot-fail-count.txt"
RECOVERY_PATH="$STATE_DIR/recovery-mode.json"
if [[ -f "$RECOVERY_PATH" ]]; then
	echo "OS Switcher is in recovery mode. Inspect $RECOVERY_PATH, fix boot health, then run mark-boot-success." >&2
	exit 1
fi

if [[ ! -f "$PENDING_PATH" && -f "$STAGED_PATH" ]]; then
	STAGED_AGE_SECONDS="$(
		python3 - "$STAGED_PATH" <<'PY'
import json
import sys
from datetime import datetime, timezone

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    staged = json.load(handle)

started = datetime.fromisoformat(staged["startedAt"].replace("Z", "+00:00"))
print(int((datetime.now(timezone.utc) - started).total_seconds()))
PY
	)"
	if [[ "$STAGED_AGE_SECONDS" -lt "$((PENDING_TIMEOUT_MINUTES * 60))" ]]; then
		echo "A transition is staged but not complete. Wait for it to finish, or inspect $STAGED_PATH." >&2
		exit 1
	fi

	mv "$STAGED_PATH" "$STATE_DIR/failed-staged-transition-$(date -u +%Y%m%d-%H%M%S).json"
	echo "A stale staged transition was found and archived. Inspect $STATE_DIR." >&2
	exit 1
fi

if [[ -f "$PENDING_PATH" ]]; then
	PENDING_AGE_SECONDS="$(
		python3 - "$PENDING_PATH" <<'PY'
import json
import sys
from datetime import datetime, timezone

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    pending = json.load(handle)

started = datetime.fromisoformat(pending["startedAt"].replace("Z", "+00:00"))
print(int((datetime.now(timezone.utc) - started).total_seconds()))
PY
	)"
	if [[ "$PENDING_AGE_SECONDS" -lt "$((PENDING_TIMEOUT_MINUTES * 60))" ]]; then
		echo "A transition is already pending. Run mark-boot-success after a successful boot, or remove $PENDING_PATH if this is stale." >&2
		exit 1
	fi

	FAIL_COUNT=0
	if [[ -f "$FAIL_COUNT_PATH" ]]; then
		FAIL_COUNT="$(cat "$FAIL_COUNT_PATH")"
	fi
	FAIL_COUNT=$((FAIL_COUNT + 1))
	printf '%s\n' "$FAIL_COUNT" >"$FAIL_COUNT_PATH"

	mv "$PENDING_PATH" "$STATE_DIR/failed-transition-$(date -u +%Y%m%d-%H%M%S).json"

	if [[ "$FAIL_COUNT" -ge "$CONFIG_MAX_BOOT_FAILURES" ]]; then
		python3 - "$RECOVERY_PATH" "$FAIL_COUNT" "$CONFIG_MAX_BOOT_FAILURES" <<'PY'
import json
import sys
from datetime import datetime, timezone

recovery_path, fail_count, threshold = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
recovery = {
    "enteredAt": datetime.now(timezone.utc).isoformat(),
    "bootFailCount": fail_count,
    "threshold": threshold,
}

with open(recovery_path, "w", encoding="utf-8") as handle:
    json.dump(recovery, handle, indent=2)
    handle.write("\n")
PY
		echo "Previous transition exceeded ${PENDING_TIMEOUT_MINUTES} minutes. Recovery mode is now active at $RECOVERY_PATH." >&2
		exit 1
	fi

	echo "Previous transition exceeded ${PENDING_TIMEOUT_MINUTES} minutes and was marked failed (${FAIL_COUNT}/${CONFIG_MAX_BOOT_FAILURES}). Inspect $STATE_DIR." >&2
	exit 1
fi

if [[ -n "$EFIBOOTMGR_OUTPUT_PATH" ]]; then
	if [[ ! -f "$EFIBOOTMGR_OUTPUT_PATH" ]]; then
		echo "efibootmgr output fixture not found: $EFIBOOTMGR_OUTPUT_PATH" >&2
		exit 1
	fi
	ENTRY_LINES="$(grep -E '^Boot[0-9A-Fa-f]{4}\*?' "$EFIBOOTMGR_OUTPUT_PATH" || true)"
else
	ENTRY_LINES="$(efibootmgr | grep -E '^Boot[0-9A-Fa-f]{4}\*?' || true)"
fi
MATCHES="$(printf '%s\n' "$ENTRY_LINES" | grep -F -i -- "$TARGET_LABEL" || true)"
MATCH_COUNT="$(printf '%s\n' "$MATCHES" | sed '/^$/d' | wc -l | tr -d ' ')"

if [[ "$MATCH_COUNT" == "0" ]]; then
	echo "No EFI boot entry matched '$TARGET_LABEL'. Available entries:" >&2
	printf '%s\n' "$ENTRY_LINES" >&2
	exit 1
fi

if [[ "$MATCH_COUNT" != "1" ]]; then
	echo "Multiple EFI boot entries matched '$TARGET_LABEL'. Make the config label more specific:" >&2
	printf '%s\n' "$MATCHES" >&2
	exit 1
fi

TARGET_LINE="$MATCHES"
TARGET_ID="$(printf '%s\n' "$TARGET_LINE" | sed -E 's/^Boot([0-9A-Fa-f]{4}).*/\1/')"

echo "Target Windows EFI entry: $TARGET_LINE"

if [[ "$DRY_RUN" == "1" || "$REBOOT" != "1" ]]; then
	echo "Dry run: would run sudo efibootmgr -n $TARGET_ID"
	echo "Dry run: would write pending transition state."
	echo "Dry run: would reboot after $REBOOT_DELAY seconds."
	exit 0
fi

if [[ "$EUID" -ne 0 ]]; then
	echo "Run this script with sudo for real switching." >&2
	exit 1
fi

if [[ "$CONFIG_REQUIRE_CONFIRMATION" == "1" && "$FORCE" != "1" ]]; then
	read -r -p "Set next boot to '$TARGET_LINE' and reboot? Type SWITCH to continue: " ANSWER
	if [[ "$ANSWER" != "SWITCH" ]]; then
		echo "Aborted."
		exit 1
	fi
fi

python3 - "$STAGED_PATH" "$TARGET_ID" <<'PY'
import json
import sys
from datetime import datetime, timezone

staged_path, target_id = sys.argv[1], sys.argv[2]
staged = {
    "target": "Windows",
    "identifier": target_id,
    "startedAt": datetime.now(timezone.utc).isoformat(),
    "source": "Linux",
    "state": "staged",
}

with open(staged_path, "w", encoding="utf-8") as handle:
    json.dump(staged, handle, indent=2)
    handle.write("\n")
PY

if efibootmgr -n "$TARGET_ID"; then
	python3 - "$PENDING_PATH" "$TARGET_ID" <<'PY'
import json
import sys
from datetime import datetime, timezone

pending_path, target_id = sys.argv[1], sys.argv[2]
now = datetime.now(timezone.utc).isoformat()
pending = {
    "target": "Windows",
    "identifier": target_id,
    "startedAt": now,
    "commandSucceededAt": now,
    "source": "Linux",
    "state": "pending",
}

with open(pending_path, "w", encoding="utf-8") as handle:
    json.dump(pending, handle, indent=2)
    handle.write("\n")
PY
	rm -f "$STAGED_PATH"
else
	rm -f "$STAGED_PATH"
	exit 1
fi
if [[ "$REBOOT_DELAY" =~ ^[0-9]+$ && "$REBOOT_DELAY" -gt 0 ]]; then
	sleep "$REBOOT_DELAY"
fi
systemctl reboot
