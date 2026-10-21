#!/usr/bin/env bash
# 线上升级（venv + systemd）：备份 -> 解压 -> 重装后端 -> 迁移 -> 重启 -> 冒烟
#
# 前置：新版本包已上传到 /opt/deploy.tgz
# 用法：bash /opt/1plus1/deploy/upgrade_remote.sh
#
# 与 release_remote.sh 的差别：后端是**非 editable** 安装，仅解压 + 重启不会让新代码
# 生效，必须 force-reinstall；表结构变更还需 alembic upgrade head。
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/1plus1}"
PORT="${PORT:-8010}"
PKG="${PKG:-/opt/deploy.tgz}"
ENV_FILE="${ENV_FILE:-/etc/1plus1.env}"
SERVICE="${SERVICE:-1plus1}"

echo "==> 1/6 备份数据库"
"$APP_DIR/venv/bin/python" - <<'PY'
import sqlite3
conn = sqlite3.connect("/opt/1plus1/data/app.db")
print("wal_checkpoint:", conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone())
conn.close()
PY
TS=$(date +%Y%m%d-%H%M)
cd "$APP_DIR"
cp data/app.db "data/app.db.bak.$TS"
cp data/app.db-wal "data/app.db-wal.bak.$TS" 2>/dev/null || true
cp data/app.db-shm "data/app.db-shm.bak.$TS" 2>/dev/null || true
echo "backup tag: $TS"

echo "==> 2/6 解压新版本"
tar -xzf "$PKG" -C "$APP_DIR"

echo "==> 3/6 重装后端（非 editable 安装，必须重装才生效）"
"$APP_DIR/venv/bin/pip" install --quiet --no-deps --no-build-isolation \
  --force-reinstall "$APP_DIR/backend"

echo "==> 4/6 数据库迁移"
set -a
. "$ENV_FILE"
set +a
cd "$APP_DIR/backend"
"$APP_DIR/venv/bin/alembic" upgrade head
echo -n "current: "
"$APP_DIR/venv/bin/alembic" current 2>/dev/null | tail -1

echo "==> 5/6 重启服务"
systemctl restart "$SERVICE"
sleep 6
echo -n "service: "
systemctl is-active "$SERVICE"

echo "==> 6/6 冒烟"
curl -fsS "http://127.0.0.1:${PORT}/api/health"; echo
curl -s -o /dev/null -w "home http=%{http_code}\n" "http://127.0.0.1:${PORT}/"
curl -s -o /dev/null -w "grammar no-auth http=%{http_code} (expect 401)\n" \
  "http://127.0.0.1:${PORT}/api/grammar/outline"
echo "--- 最近备份 ---"
ls -1t "$APP_DIR/data" | head -4
