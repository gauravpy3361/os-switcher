#!/usr/bin/env bats

# Tests for linux/rollback.sh
# Requires: bats-core, python3 (for validate_config.py)

setup() {
	ROOT="${PROJECT_ROOT:-$(cd "$BATS_TEST_DIRNAME/.." && pwd)}"
	STATE_DIR="$(mktemp -d)"
	CONFIG_PATH="$BATS_TEST_TMPDIR/config.json"
	cat >"$CONFIG_PATH" <<JSON
{
  "windows": {
    "targetLabel": "Linux Workspace",
    "rebootTimeoutSeconds": 5,
    "stateDir": "C:\\\\ProgramData\\\\OSSwitcher"
  },
  "linux": {
    "targetLabel": "Windows Boot Manager",
    "rebootDelaySeconds": 5,
    "stateDir": "$STATE_DIR"
  },
  "safety": {
    "requireConfirmation": true,
    "pendingTransitionTimeoutMinutes": 10,
    "maxBootFailures": 3
  }
}
JSON
}

teardown() {
	rm -rf "$STATE_DIR"
}

@test "rollback exits 0 and says no recovery when recovery-mode.json is absent" {
	run bash "$ROOT/linux/rollback.sh" --config "$CONFIG_PATH"

	[ "$status" -eq 0 ]
	[[ "$output" == *"No recovery mode active"* ]]
}

@test "rollback exits 1 and prints RECOVERY MODE ACTIVE when recovery-mode.json exists" {
	echo '{"recoveryAt":"2026-05-20T00:00:00Z","reason":"consecutive boot failures"}' \
		>"$STATE_DIR/recovery-mode.json"

	run bash "$ROOT/linux/rollback.sh" --config "$CONFIG_PATH"

	[ "$status" -eq 1 ]
	[[ "$output" == *"RECOVERY MODE ACTIVE"* ]]
}

@test "rollback prints newest backup path when backup file exists" {
	echo '{"recoveryAt":"2026-05-20T00:00:00Z"}' >"$STATE_DIR/recovery-mode.json"
	echo "BootCurrent: 0001" >"$STATE_DIR/efi-backup-20260520-120000.txt"

	run bash "$ROOT/linux/rollback.sh" --config "$CONFIG_PATH"

	[ "$status" -eq 1 ]
	[[ "$output" == *"efi-backup-20260520-120000.txt"* ]]
}

@test "rollback prints no backup message when no backup files exist" {
	echo '{"recoveryAt":"2026-05-20T00:00:00Z"}' >"$STATE_DIR/recovery-mode.json"

	run bash "$ROOT/linux/rollback.sh" --config "$CONFIG_PATH"

	[ "$status" -eq 1 ]
	[[ "$output" == *"No backup files found"* ]]
}

@test "rollback accepts --config argument and reads state from it" {
	# State dir from config should be respected (not a hardcoded path)
	OTHER_STATE="$(mktemp -d)"
	OTHER_CONFIG="$BATS_TEST_TMPDIR/other-config.json"
	cat >"$OTHER_CONFIG" <<JSON
{
  "windows": { "targetLabel": "Linux Workspace", "rebootTimeoutSeconds": 5, "stateDir": "C:\\\\ProgramData\\\\OSSwitcher" },
  "linux": { "targetLabel": "Windows Boot Manager", "rebootDelaySeconds": 5, "stateDir": "$OTHER_STATE" },
  "safety": { "requireConfirmation": true, "pendingTransitionTimeoutMinutes": 10, "maxBootFailures": 3 }
}
JSON
	echo '{"recoveryAt":"2026-05-20T00:00:00Z"}' >"$OTHER_STATE/recovery-mode.json"

	run bash "$ROOT/linux/rollback.sh" --config "$OTHER_CONFIG"

	[ "$status" -eq 1 ]
	[[ "$output" == *"RECOVERY MODE ACTIVE"* ]]
	rm -rf "$OTHER_STATE"
}
