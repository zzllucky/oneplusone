#!/usr/bin/env bash
# 线上升级：备份数据库 -> 解压新版本 -> 重启服务 -> 冒烟
set -euo pipefail

cd /opt/1plus1

echo "==> 1/4 备份数据库"
/opt/1plus1/venv/bin/python - <<'PY'
import sqlite3
c = sqlite3.connect("/opt/1plus1/data/app.db")
print("wal_checkpoint:", c.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone())
c.close()
PY
TS=$(date +%Y%m%d-%H%M)
cp data/app.db "data/app.db.bak.$TS"
cp data/app.db-wal "data/app.db-wal.bak.$TS" 2>/dev/null || true
cp data/app.db-shm "data/app.db-shm.bak.$TS" 2>/dev/null || true
echo "backup tag: $TS"

echo "==> 2/4 解压新版本"
tar -xzf /opt/deploy.tgz -C /opt/1plus1

echo "==> 3/4 重启服务"
systemctl restart 1plus1
sleep 5

echo "==> 4/4 冒烟"
echo -n "health: "
curl -fsS http://127.0.0.1:8010/api/health
echo
echo -n "service: "
systemctl is-active 1plus1
ls -l /opt/1plus1/frontend/dist/sounds/streak_3.mp3
curl -s -o /dev/null -w "mp3 http=%{http_code} type=%{content_type} size=%{size_download}\n" \
  http://127.0.0.1:8010/sounds/streak_3.mp3
curl -s -o /dev/null -w "home http=%{http_code}\n" http://127.0.0.1:8010/
echo "--- 最近备份 ---"
ls -1t /opt/1plus1/data | head -4
