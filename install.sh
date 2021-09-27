#!/bin/bash

set -ex

if [[ $USER != "root" ]]; then
  exec sudo "$0" "$@"
fi

DIR=$(realpath $(dirname $0))
SERVICE='ont-reboot.service'
SYSTEM='/lib/systemd/system'
SCRIPT='ont-reboot.py'

rm -f $SYSTEM/$SERVICE
cat > $SYSTEM/$SERVICE << EOF
[Unit]
Description=ONT Reboot Service
ConditionPathExists=$DIR/$SCRIPT
After=network.target

[Service]
ExecStart=python3 $DIR/$SCRIPT

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE
systemctl restart $SERVICE
