#!/bin/bash

set -euxo pipefail

APP_NAME="xmas-lights"
CURRENT_DIR=$(realpath "$(dirname "$0")")

curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv venv --allow-existing "$CURRENT_DIR/.venv"
uv sync --directory "$CURRENT_DIR" --no-dev --group prod

cat > "/etc/systemd/system/$APP_NAME.service" << EOF
[Unit]
Description=Xmas Lights Service
After=time-sync.service

[Service]
ExecStart="$CURRENT_DIR/.venv/bin/python" -u "$CURRENT_DIR/app.py" --led-count 140
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$APP_NAME"
systemctl restart "$APP_NAME"
