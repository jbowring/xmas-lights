#!/bin/sh

set -e

name="xmaslights"
dir=$(dirname "$0")

apt update
apt install python3-pip -y
pip3 install -r "$dir/requirements.txt"
cp "$dir/$name.service" /lib/systemd/system/
systemctl daemon-reload
systemctl enable "$name"
chmod +x "$dir/app.py"
service "$name" restart
