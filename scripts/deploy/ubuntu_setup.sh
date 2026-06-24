#!/usr/bin/env bash
# 在 Ubuntu 22.04 服务器上执行（由 deploy.ps1 远程调用，也可手动运行）
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/sensehub}"
DOMAIN="${DOMAIN:-_}"
APP_USER="${APP_USER:-www-data}"
SKIP_NPM_BUILD="${SKIP_NPM_BUILD:-1}"

echo "==> SenseHub 服务器安装 @ ${APP_ROOT}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "请使用 root 运行，或: sudo bash $0"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx python3-venv python3-pip curl ca-certificates rsync

# 2GB 内存：swap
if ! swapon --show | grep -q /swapfile; then
  echo "==> 配置 2GB swap"
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

mkdir -p "${APP_ROOT}/data/db" "${APP_ROOT}/data/screenshots"
chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}/data" 2>/dev/null || true

# Python 虚拟环境
if [[ ! -d "${APP_ROOT}/.venv" ]]; then
  echo "==> 创建 Python venv"
  python3 -m venv "${APP_ROOT}/.venv"
fi
"${APP_ROOT}/.venv/bin/pip" install -U pip wheel -q
"${APP_ROOT}/.venv/bin/pip" install -e "${APP_ROOT}" -q

# 前端：优先使用本地上传的 dist；否则在服务器构建（2G 可能较慢）
if [[ "${SKIP_NPM_BUILD}" == "1" && -f "${APP_ROOT}/web/dist/index.html" ]]; then
  echo "==> 使用已上传的 web/dist"
else
  echo "==> 服务器构建前端（建议本机 deploy.ps1 预构建）"
  if ! command -v node >/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
  fi
  cd "${APP_ROOT}/web"
  npm ci --prefer-offline --no-audit --no-fund
  npm run build
fi

# 确保 local.env 存在
if [[ ! -f "${APP_ROOT}/config/local.env" ]]; then
  echo "警告: ${APP_ROOT}/config/local.env 不存在，请从本机上传后重启服务"
  cp "${APP_ROOT}/config/local.env.example" "${APP_ROOT}/config/local.env" || true
fi

# 将 Windows 开发路径覆盖为 Linux 生产路径
ENV_FILE="${APP_ROOT}/config/local.env"
set_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}
set_env "SENSEHUB_ROOT" "${APP_ROOT}"
set_env "DATA_ROOT" "${APP_ROOT}/data"
set_env "SQLITE_PATH" "${APP_ROOT}/data/db/sensehub.db"
set_env "API_HOST" "127.0.0.1"
set_env "API_PORT" "8765"
set_env "USE_CUDA" "false"
set_env "TTS_ENABLED" "false"
if [[ "${DOMAIN}" != "_" ]]; then
  set_env "OAUTH_FRONTEND_URL" "http://${DOMAIN}"
fi

for f in models.yaml policies.yaml; do
  if [[ ! -f "${APP_ROOT}/config/${f}" ]]; then
    cp "${APP_ROOT}/config/${f}.example" "${APP_ROOT}/config/${f}" 2>/dev/null || true
  fi
done

# systemd
cat > /etc/systemd/system/sensehub.service << EOF
[Unit]
Description=SenseHub Agent API
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_ROOT}
Environment=PATH=${APP_ROOT}/.venv/bin
ExecStart=${APP_ROOT}/.venv/bin/python -m sensehub.main
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# nginx
cat > /etc/nginx/sites-available/sensehub << EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name ${DOMAIN};

    root ${APP_ROOT}/web/dist;
    index index.html;

    client_max_body_size 20m;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 3600s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8765;
    }

    location /screenshots/ {
        proxy_pass http://127.0.0.1:8765;
    }
}
EOF

ln -sf /etc/nginx/sites-available/sensehub /etc/nginx/sites-enabled/sensehub
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
nginx -t

chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}/data" "${APP_ROOT}/config" 2>/dev/null || true
chmod 600 "${APP_ROOT}/config/local.env" 2>/dev/null || true

systemctl daemon-reload
systemctl enable sensehub nginx
systemctl restart sensehub
systemctl reload nginx

sleep 2
if curl -sf http://127.0.0.1:8765/health >/dev/null; then
  echo "==> 后端健康检查通过"
else
  echo "==> 警告: 后端未响应，请检查 journalctl -u sensehub -n 50"
fi

echo ""
echo "部署完成。访问: http://${DOMAIN}/"
echo "日志: journalctl -u sensehub -f"
