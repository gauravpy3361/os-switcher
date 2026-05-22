#!/usr/bin/env bats

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

@test "linux switch dry run uses fixture output without writing pending state" {
	run "$ROOT/linux/switch-to-windows.sh" \
		--config "$CONFIG_PATH" \
		--dry-run \
		--efibootmgr-output "$ROOT/tests/fixtures/efibootmgr.txt"

	[ "$status" -eq 0 ]
	[[ "$output" == *"Target Windows EFI entry"* ]]
	[[ "$output" == *"Dry run: would run sudo efibootmgr -n 0000"* ]]
	[ ! -f "$STATE_DIR/pending-transition.json" ]
}

@test "linux boot success clears pending only when Linux was the target" {
	cat >"$STATE_DIR/pending-transition.json" <<JSON
{
  "target": "Linux",
  "identifier": "0001",
  "startedAt": "2026-05-20T00:00:00+00:00",
  "source": "Windows",
  "state": "pending"
}
JSON

	run "$ROOT/linux/mark-boot-success.sh" --config "$CONFIG_PATH"

	[ "$status" -eq 0 ]
	[ ! -f "$STATE_DIR/pending-transition.json" ]
	[ -f "$STATE_DIR/last-boot-success.json" ]
}

@test "linux boot success records failure when Windows was the target" {
	cat >"$STATE_DIR/pending-transition.json" <<JSON
{
  "target": "Windows",
  "identifier": "0000",
  "startedAt": "2026-05-20T00:00:00+00:00",
  "source": "Linux",
  "state": "pending"
}
JSON

	run "$ROOT/linux/mark-boot-success.sh" --config "$CONFIG_PATH"

	[ "$status" -eq 1 ]
	[[ "$output" == *"Boot target mismatch recorded"* ]]
	[ ! -f "$STATE_DIR/pending-transition.json" ]
	[ -f "$STATE_DIR/boot-fail-count.txt" ]
	[ -f "$STATE_DIR/last-boot-mismatch.json" ]
}

@test "linux switch archives stale staged transition" {
	# Write a staged transition dated 15 minutes ago (timeout is 10 minutes)
	STALE_TIME="$(python3 -c 'from datetime import datetime, timedelta, timezone; print((datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat().replace("+00:00", "Z"))')"

	cat >"$STATE_DIR/transition-staged.json" <<JSON
{
  "target": "Windows",
  "identifier": "0000",
  "startedAt": "$STALE_TIME",
  "source": "Linux",
  "state": "staged"
}
JSON

	run "$ROOT/linux/switch-to-windows.sh" --config "$CONFIG_PATH" --dry-run

	[ "$status" -eq 1 ]
	[[ "$output" == *"A stale staged transition was found and archived"* ]]
	[ ! -f "$STATE_DIR/transition-staged.json" ]

	ARCHIVED_COUNT="$(find "$STATE_DIR" -name "failed-staged-transition-*.json" | wc -l | tr -d ' ')"
	[ "$ARCHIVED_COUNT" -eq 1 ]
}

