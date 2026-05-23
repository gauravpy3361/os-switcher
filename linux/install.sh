#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/os-switcher"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

echo "========================================"
echo "  OS Switcher Installer — Linux"
echo "========================================"
echo ""

# --- Step 1: Check root ---
if [[ "$EUID" -ne 0 ]]; then
	echo "ERROR: This installer must be run as root." >&2
	echo "Usage: sudo bash $0" >&2
	exit 1
fi

# --- Step 2: Check Python 3.8+ ---
if ! command -v python3 >/dev/null 2>&1; then
	echo "ERROR: python3 is not installed." >&2
	exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTHON_MAJOR="$(python3 -c 'import sys; print(sys.version_info.major)')"
PYTHON_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"

if [[ "$PYTHON_MAJOR" -lt 3 ]] || { [[ "$PYTHON_MAJOR" -eq 3 ]] && [[ "$PYTHON_MINOR" -lt 8 ]]; }; then
	echo "ERROR: Python 3.8+ is required. Current version: $PYTHON_VERSION" >&2
	exit 1
fi
echo "OK   Python $PYTHON_VERSION detected."

# --- Step 3: Check efibootmgr ---
if ! command -v efibootmgr >/dev/null 2>&1; then
	echo "ERROR: efibootmgr is not installed." >&2
	echo "Install it with: sudo dnf install efibootmgr" >&2
	exit 1
fi
echo "OK   efibootmgr detected."

# --- Step 3b: Check rsync ---
if ! command -v rsync >/dev/null 2>&1; then
	echo "ERROR: rsync is not installed." >&2
	echo "Install it with: sudo dnf install rsync" >&2
	exit 1
fi
echo "OK   rsync detected."

# --- Step 4: Copy project files to /opt/os-switcher ---
echo ""
echo "Installing to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"

rsync -a --delete \
	--exclude='config.json' \
	--exclude='__pycache__' \
	--exclude='.git' \
	--exclude='dist' \
	--exclude='tests' \
	"$PROJECT_ROOT/" "$INSTALL_DIR/"

echo "OK   Project files copied to $INSTALL_DIR."

# --- Step 5: Copy example config if no config.json exists ---
if [[ ! -f "$INSTALL_DIR/config.json" ]]; then
	cp "$INSTALL_DIR/config.example.json" "$INSTALL_DIR/config.json"
	echo "OK   config.example.json copied to config.json (edit before first use)."
else
	echo "OK   Existing config.json preserved."
fi

# --- Step 6: Make scripts executable ---
chmod +x "$INSTALL_DIR/linux/switch-to-windows.sh"
chmod +x "$INSTALL_DIR/linux/mark-boot-success.sh"
chmod +x "$INSTALL_DIR/linux/rollback.sh"
chmod +x "$INSTALL_DIR/linux/install-boot-success-service.sh"
chmod +x "$INSTALL_DIR/linux/uninstall-boot-success-service.sh"
chmod +x "$INSTALL_DIR/linux/status-boot-success-service.sh"
echo "OK   Linux scripts marked executable."

# --- Step 7: Install boot-success systemd service ---
echo ""
echo "Installing boot-success systemd service ..."
bash "$INSTALL_DIR/linux/install-boot-success-service.sh"
echo "OK   Boot-success service installed."

# --- Step 8: Create symlink ---
ln -sf "$INSTALL_DIR/gui/os_switcher_gui.py" /usr/local/bin/os-switcher
chmod +x "$INSTALL_DIR/gui/os_switcher_gui.py"
echo "OK   Symlink created: /usr/local/bin/os-switcher"

# --- Done ---
echo ""
echo "========================================"
echo "  Installation complete."
echo "========================================"
echo ""
echo "Next: Edit /opt/os-switcher/config.json with your EFI GUIDs."
echo "Then run: os-switcher"
