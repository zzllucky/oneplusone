#!/usr/bin/env bash
# 1+1=2 —— 云服务器一键部署（Ubuntu 24.04，Python venv + systemd）
#
# 前置：代码已解压到 /opt/1plus1（backend/、frontend/dist/）
# 用法：JWT_SECRET=<随机串> bash /opt/1plus1/deploy/deploy.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/1plus1}"
PORT="${PORT:-8010}"
JWT_SECRET="${JWT_SECRET:-}"

if [ -z "$JWT_SECRET" ]; then
  echo "ERROR: 必须提供 JWT_SECRET（例：JWT_SECRET=\$(openssl rand -base64 48)）" >&2
  exit 1
fi

echo "==> 1/6 安装系统依赖"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip

echo "==> 2/6 创建虚拟环境并安装后端"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
# 非 editable 安装：更新 backend/src 后必须重装才会生效
#   /opt/1plus1/venv/bin/pip install --no-deps --force-reinstall /opt/1plus1/backend
#   systemctl restart 1plus1
"$APP_DIR/venv/bin/pip" install --quiet "$APP_DIR/backend"

echo "==> 3/6 写入环境配置 /etc/1plus1.env"
mkdir -p "$APP_DIR/data/cache/pronounce"
cat >/etc/1plus1.env <<EOF
JWT_SECRET=$JWT_SECRET
DB_PATH=$APP_DIR/data/app.db
PRONOUNCE_CACHE_DIR=$APP_DIR/data/cache/pronounce
STATIC_DIR=$APP_DIR/frontend/dist
TIMEZONE=Asia/Shanghai
EOF
chmod 600 /etc/1plus1.env

echo "==> 4/6 执行数据库迁移并导入词表"
set -a
. /etc/1plus1.env
set +a
cd "$APP_DIR/backend"
"$APP_DIR/venv/bin/alembic" upgrade head

echo "==> 5/6 注册 systemd 服务并放行端口"
cat >/etc/systemd/system/1plus1.service <<EOF
[Unit]
Description=1+1=2 word study service
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=/etc/1plus1.env
ExecStart=$APP_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now 1plus1
ufw allow ${PORT}/tcp >/dev/null 2>&1 || true

echo "==> 6/6 健康检查"
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    echo "服务已就绪: http://<服务器公网IP>:${PORT}"
    curl -s "http://127.0.0.1:${PORT}/api/health"; echo
    exit 0
  fi
  sleep 2
done

echo "健康检查超时，查看日志：journalctl -u 1plus1 -n 50" >&2
systemctl status 1plus1 --no-pager | tail -20 || true
exit 1
