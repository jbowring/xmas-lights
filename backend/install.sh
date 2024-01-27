#!/bin/bash

set -e

APP_NAME="xmas-lights"
CURRENT_DIR=$(dirname "$0")

apt update
apt install python3-pip python3-venv -y
python3 -m venv "$CURRENT_DIR/venv"
"$CURRENT_DIR/venv/bin/pip" install -r "$CURRENT_DIR/requirements.txt"

cat > "/etc/systemd/system/$APP_NAME.service" << EOF
[Unit]
Description=Xmas Lights Service
After=time-sync.service

[Service]
ExecStart="$CURRENT_DIR/venv/bin/python" -u "$CURRENT_DIR/app.py" --led-count 200
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$APP_NAME"
systemctl restart "$APP_NAME"
