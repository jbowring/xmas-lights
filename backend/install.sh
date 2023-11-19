#!/bin/sh

set -e

name="xmaslights"
dir=$(dirname "$0")

if systemctl is-active --quiet "$name"
then
  systemctl stop "$name"
fi

apt update
apt install python3-pip -y
pip3 install -r "$dir/requirements.txt"
cp "$dir/$name.service" /lib/systemd/system/
systemctl daemon-reload
systemctl enable "$name"
chmod +x "$dir/app.py"
systemctl start "$name"
