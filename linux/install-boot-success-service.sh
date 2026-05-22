#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="$SCRIPT_DIR/../config.json"
SERVICE_PATH="/etc/systemd/system/os-switcher-boot-success.service"
WRAPPER_DIR="/usr/local/lib/os-switcher"
WRAPPER_PATH="$WRAPPER_DIR/mark-boot-success-wrapper.sh"

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

if [[ "$EUID" -ne 0 ]]; then
	echo "Run this installer with sudo." >&2
	exit 1
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
	echo "Config file not found: $CONFIG_PATH" >&2
	exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
	echo "systemctl is required to install the boot-success service." >&2
	exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
	echo "python3 is required to validate config.json." >&2
	exit 1
fi

python3 "$SCRIPT_DIR/../tools/validate_config.py" "$CONFIG_PATH" >/dev/null

MARK_SCRIPT="$(realpath "$SCRIPT_DIR/mark-boot-success.sh")"
RESOLVED_CONFIG="$(realpath "$CONFIG_PATH")"

mkdir -p "$WRAPPER_DIR"
cat >"$WRAPPER_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$MARK_SCRIPT" --config "$RESOLVED_CONFIG"
EOF
chmod 0755 "$WRAPPER_PATH"

cat >"$SERVICE_PATH" <<EOF
[Unit]
Description=Mark OS Switcher boot success
After=multi-user.target

[Service]
Type=oneshot
User=root
RemainAfterExit=yes
ExecStart=$WRAPPER_PATH

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable os-switcher-boot-success.service

echo "Installed and enabled $SERVICE_PATH"
