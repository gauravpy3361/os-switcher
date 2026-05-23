#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/os-switcher"
SYMLINK_PATH="/usr/local/bin/os-switcher"

echo "========================================"
echo "  OS Switcher Uninstaller — Linux"
echo "========================================"
echo ""

# --- Step 1: Check root ---
if [[ "$EUID" -ne 0 ]]; then
	echo "ERROR: This uninstaller must be run as root." >&2
	echo "Usage: sudo bash $0" >&2
	exit 1
fi

# --- Step 2: Remove boot-success systemd service ---
echo "Removing boot-success systemd service ..."
if [[ -f "$INSTALL_DIR/linux/uninstall-boot-success-service.sh" ]]; then
	bash "$INSTALL_DIR/linux/uninstall-boot-success-service.sh" || true
	echo "OK   Boot-success service removed."
else
	echo "SKIP Service uninstall script not found (already removed?)."
fi

# --- Step 3: Remove symlink ---
if [[ -L "$SYMLINK_PATH" ]]; then
	rm -f "$SYMLINK_PATH"
	echo "OK   Symlink removed: $SYMLINK_PATH"
else
	echo "SKIP Symlink not found: $SYMLINK_PATH"
fi

# --- Step 4: Remove install directory ---
if [[ -d "$INSTALL_DIR" ]]; then
	rm -rf "$INSTALL_DIR"
	echo "OK   Removed install directory: $INSTALL_DIR"
else
	echo "SKIP Install directory not found: $INSTALL_DIR"
fi

# --- Done ---
echo ""
echo "========================================"
echo "  Uninstall complete."
echo "========================================"
echo ""
echo "NOTE: Your state directory was NOT removed."
echo "      It may contain transition state and EFI backups."
echo "      To find it, check the stateDir value in your config."
