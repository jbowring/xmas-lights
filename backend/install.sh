#!/bin/bash

set -euxo pipefail

APP_NAME="xmas-lights"
CURRENT_DIR=$(realpath "$(dirname "$0")")
CONFIG_DIR="/var/lib/xmas-lights"
CONFIG_FILE="$CONFIG_DIR/config.toml"

curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv venv --allow-existing "$CURRENT_DIR/.venv"
uv sync --directory "$CURRENT_DIR" --no-dev --group prod

if [ ! -f "$CONFIG_FILE" ]; then
  mkdir -p "$CONFIG_DIR"
  echo "Creating default configuration at $CONFIG_FILE"
  cat > "$CONFIG_FILE" << EOF
led_count = 100
# plugins_dir = "$CONFIG_DIR/plugins/"
# patterns_file = "$CONFIG_DIR/patterns.json"

# [plugins.teams]
# enabled = true
# tenant_id = "YOUR_TENANT_ID"
# client_id = "YOUR_CLIENT_ID"
# people_site = "YOUR_SITE_ID"
# people_list = "YOUR_LIST_ID"
# people_user_info_list = "YOUR_USER_INFO_LIST_ID"
EOF
fi

cat > "/etc/systemd/system/$APP_NAME.service" << EOF
[Unit]
Description=Xmas Lights Service
After=time-sync.service

[Service]
ExecStart="$CURRENT_DIR/.venv/bin/python" -u "$CURRENT_DIR/app.py" --config "$CONFIG_FILE"
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$APP_NAME"
systemctl restart "$APP_NAME"
