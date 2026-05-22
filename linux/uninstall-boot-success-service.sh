#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="os-switcher-boot-success.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
WRAPPER_DIR="/usr/local/lib/os-switcher"
WRAPPER_PATH="$WRAPPER_DIR/mark-boot-success-wrapper.sh"

if [[ "$EUID" -ne 0 ]]; then
	echo "Run this uninstaller with sudo." >&2
	exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
	echo "systemctl is required to uninstall the boot-success service." >&2
	exit 1
fi

if systemctl list-unit-files "$SERVICE_NAME" >/dev/null 2>&1; then
	systemctl disable --now "$SERVICE_NAME" >/dev/null 2>&1 || true
fi

rm -f "$SERVICE_PATH" "$WRAPPER_PATH"
rmdir "$WRAPPER_DIR" 2>/dev/null || true
systemctl daemon-reload

echo "Removed $SERVICE_NAME"
