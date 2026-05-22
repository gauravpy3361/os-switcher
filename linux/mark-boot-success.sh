#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="$SCRIPT_DIR/../config.json"
CLEAR_RECOVERY=0

while [[ $# -gt 0 ]]; do
	case "$1" in
	--config)
		CONFIG_PATH="$2"
		shift 2
		;;
	--clear-recovery)
		CLEAR_RECOVERY=1
		shift
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
CONFIG_MAX_BOOT_FAILURES="$MAX_BOOT_FAILURES"
mkdir -p "$STATE_DIR"

PENDING_PATH="$STATE_DIR/pending-transition.json"
SUCCESS_PATH="$STATE_DIR/last-boot-success.json"
FAIL_COUNT_PATH="$STATE_DIR/boot-fail-count.txt"
RECOVERY_PATH="$STATE_DIR/recovery-mode.json"
MISMATCH_PATH="$STATE_DIR/last-boot-mismatch.json"
CLEARED_PENDING=0

if [[ ! -f "$PENDING_PATH" && ! -f "$FAIL_COUNT_PATH" && ! -f "$RECOVERY_PATH" ]]; then
	exit 0
fi

if [[ -f "$RECOVERY_PATH" && "$CLEAR_RECOVERY" != "1" ]]; then
	echo "Recovery mode is active at $RECOVERY_PATH. Inspect boot health, then rerun with --clear-recovery if it is safe."
	exit 0
fi

if [[ ! -f "$PENDING_PATH" && "$CLEAR_RECOVERY" != "1" ]]; then
	echo "Failure state exists in $STATE_DIR. Inspect it, then rerun with --clear-recovery if it is safe."
	exit 0
fi

if [[ -f "$PENDING_PATH" ]]; then
	PENDING_TARGET="$(
		python3 - "$PENDING_PATH" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    pending = json.load(handle)

print(str(pending.get("target", "")))
PY
	)"
	if [[ "${PENDING_TARGET,,}" != "linux" ]]; then
		FAIL_COUNT=0
		if [[ -f "$FAIL_COUNT_PATH" ]]; then
			FAIL_COUNT="$(cat "$FAIL_COUNT_PATH")"
		fi
		FAIL_COUNT=$((FAIL_COUNT + 1))
		printf '%s\n' "$FAIL_COUNT" >"$FAIL_COUNT_PATH"

		mv "$PENDING_PATH" "$STATE_DIR/failed-transition-$(date -u +%Y%m%d-%H%M%S).json"
		python3 - "$MISMATCH_PATH" "$PENDING_TARGET" "$FAIL_COUNT" <<'PY'
import json
import sys
from datetime import datetime, timezone

mismatch_path, expected_target, fail_count = sys.argv[1], sys.argv[2], int(sys.argv[3])
mismatch = {
    "os": "Linux",
    "markedAt": datetime.now(timezone.utc).isoformat(),
    "expectedTarget": expected_target,
    "bootFailCount": fail_count,
}

with open(mismatch_path, "w", encoding="utf-8") as handle:
    json.dump(mismatch, handle, indent=2)
    handle.write("\n")
PY

		if [[ "$FAIL_COUNT" -ge "$CONFIG_MAX_BOOT_FAILURES" ]]; then
			python3 - "$RECOVERY_PATH" "$FAIL_COUNT" "$CONFIG_MAX_BOOT_FAILURES" "$PENDING_TARGET" <<'PY'
import json
import sys
from datetime import datetime, timezone

recovery_path, fail_count, threshold, expected_target = (
    sys.argv[1],
    int(sys.argv[2]),
    int(sys.argv[3]),
    sys.argv[4],
)
recovery = {
    "enteredAt": datetime.now(timezone.utc).isoformat(),
    "bootFailCount": fail_count,
    "threshold": threshold,
    "reason": f"Booted Linux while pending target was '{expected_target}'.",
}

with open(recovery_path, "w", encoding="utf-8") as handle:
    json.dump(recovery, handle, indent=2)
    handle.write("\n")
PY
			echo "Boot target mismatch recorded. Recovery mode is now active at $RECOVERY_PATH." >&2
			exit 1
		fi

		echo "Boot target mismatch recorded (${FAIL_COUNT}/${CONFIG_MAX_BOOT_FAILURES}). Expected '$PENDING_TARGET' but booted Linux." >&2
		exit 1
	fi

	rm -f "$PENDING_PATH"
	CLEARED_PENDING=1
fi

rm -f "$FAIL_COUNT_PATH" "$RECOVERY_PATH"

python3 - "$SUCCESS_PATH" "$CLEARED_PENDING" <<'PY'
import json
import sys
from datetime import datetime, timezone

success_path, cleared_pending = sys.argv[1], sys.argv[2]
success = {
    "os": "Linux",
    "markedAt": datetime.now(timezone.utc).isoformat(),
    "clearedPending": cleared_pending == "1",
}

with open(success_path, "w", encoding="utf-8") as handle:
    json.dump(success, handle, indent=2)
    handle.write("\n")
PY

echo "Marked Linux boot success: $SUCCESS_PATH"
