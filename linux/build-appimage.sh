#!/usr/bin/env bash
# Script to build OS Switcher as a Linux AppImage.
# Safe for all execution paths.

set -euo pipefail

# 1. Resolve paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Building OS Switcher AppImage..."
echo "Repository root: $REPO_ROOT"

# Ensure we operate in a clean temp build directory
BUILD_DIR="$REPO_ROOT/dist/appimage-build"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 2. Check and download appimagetool if not available
if ! command -v appimagetool >/dev/null 2>&1; then
    echo "appimagetool not found on PATH. Checking local tools..."
    if [ ! -f "$REPO_ROOT/tools/appimagetool" ]; then
        echo "Downloading appimagetool..."
        mkdir -p "$REPO_ROOT/tools"
        curl -L -o "$REPO_ROOT/tools/appimagetool" "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        chmod +x "$REPO_ROOT/tools/appimagetool"
    fi
    APPIMAGETOOL="$REPO_ROOT/tools/appimagetool"
    APPIMAGETOOL_CMD="$APPIMAGETOOL --appimage-extract-and-run"
else
    APPIMAGETOOL_CMD="appimagetool"
fi

# 3. Create AppDir structure
APP_DIR="$BUILD_DIR/AppDir"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/usr/bin"
mkdir -p "$APP_DIR/opt/os-switcher"

# 4. Copy project files except ignored ones
echo "Copying project files..."
cp -r "$REPO_ROOT/"* "$APP_DIR/opt/os-switcher/" || true

# Clean up excluded directories and files
rm -rf "$APP_DIR/opt/os-switcher/.git"
rm -rf "$APP_DIR/opt/os-switcher/tests"
rm -rf "$APP_DIR/opt/os-switcher/dist"
rm -rf "$APP_DIR/opt/os-switcher/__pycache__"
rm -f "$APP_DIR/opt/os-switcher/config.json"

# 5. Create AppRun script
echo "Creating AppRun..."
cat << 'EOF' > "$APP_DIR/AppRun"
#!/usr/bin/env bash
set -e

# Resolve the AppImage mountpoint
HERE="$(dirname "$(readlink -f "$0")")"

# AppImages are read-only.
# We create a persistent config directory in the user's home config directory.
PERSISTENT_CONFIG_DIR="$HOME/.config/os-switcher"
mkdir -p "$PERSISTENT_CONFIG_DIR"
PERSISTENT_CONFIG="$PERSISTENT_CONFIG_DIR/config.json"

# Set up a writable sandbox in /tmp for python execution
SANDBOX="/tmp/os-switcher-app-$USER"
rm -rf "$SANDBOX"
mkdir -p "$SANDBOX"

# Copy execution files to writable sandbox
cp -r "$HERE/opt/os-switcher/"* "$SANDBOX/"
chmod +x "$SANDBOX/linux/"*.sh
chmod +x "$SANDBOX/windows/"*.ps1 2>/dev/null || true

# Use system-wide config if available and persistent doesn't exist
if [ -f "/etc/os-switcher/config.json" ] && [ ! -f "$PERSISTENT_CONFIG" ]; then
    cp "/etc/os-switcher/config.json" "$PERSISTENT_CONFIG"
fi

# Symlink persistent config to the execution sandbox
if [ -f "$PERSISTENT_CONFIG" ]; then
    ln -sf "$PERSISTENT_CONFIG" "$SANDBOX/config.json"
fi

cd "$SANDBOX"

# If config.json doesn't exist, run the setup wizard
if [ ! -f "config.json" ]; then
    echo "Configuration config.json not found. Launching Setup Wizard..."
    python3 tools/setup_wizard.py --output "$PERSISTENT_CONFIG"
    ln -sf "$PERSISTENT_CONFIG" "$SANDBOX/config.json"
fi

# Launch the GUI
exec python3 gui/os_switcher_gui.py "$@"
EOF
chmod +x "$APP_DIR/AppRun"

# 6. Create usr/bin/os-switcher wrapper
echo "Creating usr/bin wrapper..."
cat << 'EOF' > "$APP_DIR/usr/bin/os-switcher"
#!/bin/sh
exec "$(dirname "$0")/../../AppRun" "$@"
EOF
chmod +x "$APP_DIR/usr/bin/os-switcher"

# 7. Create desktop entry file
echo "Creating desktop file..."
cat << 'EOF' > "$APP_DIR/os-switcher.desktop"
[Desktop Entry]
Type=Application
Name=OS Switcher
Exec=os-switcher
Icon=os-switcher
Categories=Utility;
Terminal=false
Comment=One-click dual-boot switching using UEFI boot targets
EOF

# 8. Generate placeholder icon
echo "Generating placeholder icon..."
python3 - << 'EOF'
import zlib
import struct

def make_png(width, height):
    raw_data = b""
    for y in range(height):
        raw_data += b"\x00" # Filter type 0
        for x in range(width):
            r = int(x * 255 / width)
            g = int(y * 255 / height)
            b = 255
            raw_data += bytes([r, g, b])
    png = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = b"IHDR" + ihdr_data
    png += struct.pack(">I", len(ihdr_data)) + ihdr + struct.pack(">I", zlib.crc32(ihdr))
    idat_data = zlib.compress(raw_data)
    idat = b"IDAT" + idat_data
    png += struct.pack(">I", len(idat_data)) + idat + struct.pack(">I", zlib.crc32(idat))
    iend = b"IEND"
    png += struct.pack(">I", 0) + iend + struct.pack(">I", zlib.crc32(iend))
    return png

with open("AppDir/os-switcher.png", "wb") as f:
    f.write(make_png(64, 64))
EOF

# 9. Build AppImage to dist/
mkdir -p "$REPO_ROOT/dist"
echo "Compiling AppImage..."
export ARCH=x86_64
VERSION=$(cat "$REPO_ROOT/VERSION")
$APPIMAGETOOL_CMD "$APP_DIR" "$REPO_ROOT/dist/OSSwitcher-$VERSION-x86_64.AppImage"

# 10. Clean up build directory
rm -rf "$BUILD_DIR"

echo "AppImage build complete: dist/OSSwitcher-$VERSION-x86_64.AppImage"
