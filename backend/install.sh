#!/bin/bash

set -e

APP_NAME="xmas-lights"
CURRENT_DIR=$(realpath $(dirname "$0"))

curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv venv "$CURRENT_DIR/.venv"
source "$CURRENT_DIR/.venv/bin/activate"
uv pip install -r "$CURRENT_DIR/requirements.txt"

cat > "/etc/systemd/system/$APP_NAME.service" << EOF
[Unit]
Description=Xmas Lights Service
After=time-sync.service

[Service]
ExecStart="$CURRENT_DIR/.venv/bin/python" -u "$CURRENT_DIR/app.py" --led-count 200
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$APP_NAME"
systemctl restart "$APP_NAME"
