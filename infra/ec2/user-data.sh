#!/bin/bash
set -e

# Instala Docker y compose plugin
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu || true

# Directorio de la app
mkdir -p /opt/app
chown ubuntu:ubuntu /opt/app

# Habilita arranque al boot (pull + up)
cat >/etc/systemd/system/app.service <<'UNIT'
[Unit]
Description=Compose app
After=network-online.target docker.service
Wants=docker.service

[Service]
WorkingDirectory=/opt/app
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=0
RemainAfterExit=yes
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable app.service
