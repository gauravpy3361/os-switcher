#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="os-switcher-boot-success.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
WRAPPER_PATH="/usr/local/lib/os-switcher/mark-boot-success-wrapper.sh"

if ! command -v systemctl >/dev/null 2>&1; then
	echo "systemctl is required to inspect the boot-success service." >&2
	exit 1
fi

if [[ ! -f "$SERVICE_PATH" ]]; then
	echo "Service unit is not installed: $SERVICE_PATH"
	exit 1
fi

echo "Service unit: $SERVICE_PATH"
echo "Wrapper: $WRAPPER_PATH"
systemctl is-enabled "$SERVICE_NAME" || true
systemctl status "$SERVICE_NAME" --no-pager || true
