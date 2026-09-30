# 运维说明

## 数据位置

| 内容 | 路径 |
|---|---|
| SQLite 数据库 | `data/app.db`（容器内 `/app/data/app.db`） |
| 发音音频缓存 | `data/cache/pronounce`（容器内 `/app/data/cache/pronounce`） |

两者均在卷挂载目录内，容器重建不丢失。

### 云服务器直连部署（venv + systemd）

| 项 | 路径 / 值 |
|---|---|
| 应用目录 | `/opt/1plus1`（`backend/`、`frontend/dist/`、`venv/`、`data/`） |
| 数据库 | `/opt/1plus1/data/app.db` |
| 发音缓存 | `/opt/1plus1/data/cache/pronounce` |
| 环境配置 | `/etc/1plus1.env`（600，含 `JWT_SECRET`） |
| 服务 | systemd `1plus1`（`systemctl restart 1plus1`、`journalctl -u 1plus1 -f`） |
| 部署脚本 | `deploy/deploy.sh`（`JWT_SECRET=... PORT=... bash deploy/deploy.sh`） |

升级：重新打包上传 → 覆盖文件 → `systemctl restart 1plus1`；涉及表结构变更时先 `alembic upgrade head`。
备份：停服或 `PRAGMA wal_checkpoint` 后拷贝 `/opt/1plus1/data/app.db`（连同 `-wal` / `-shm`）。

## 备份

SQLite 单文件数据库，**拷贝即备份**。建议先 `PRAGMA wal_checkpoint` 或直接停服后拷贝：

```bash
docker compose stop web
cp data/app.db data/app.db.bak.$(date +%Y%m%d)
cp data/app.db-wal data/app.db-wal.bak.$(date +%Y%m%d) 2>/dev/null || true
cp data/app.db-shm data/app.db-shm.bak.$(date +%Y%m%d) 2>/dev/null || true
docker compose start web
```

恢复：停服后用备份文件覆盖 `data/app.db`（并删除 `-wal` / `-shm`），再启动。

## 升级发布步骤

1. **备份** `data/app.db`（见上）
2. 构建新镜像：`docker compose build`
3. 执行迁移：`docker compose run --rm web alembic upgrade head`
   - `001` 建立全部业务表
   - `002` 按 `spelling` **幂等 upsert** 导入词表种子（重复执行结果不变，不删用户数据）
4. 启动：`docker compose up -d`
5. 冒烟：
   - `curl localhost:8000/api/health` → `{"status":"ok"}`
   - 注册 → 设置目标 → 学习 → 标记浏览 → 开始测验 → 答错 → 查看错题本 → 专项练习答对 → 错题消失

## 回滚

- 代码：回滚到旧镜像 tag
- 数据迁移：`alembic downgrade 001` 会清空 `words` 表（002 的 downgrade），需要重新 `upgrade head` 导入；更安全的做法是**用备份文件恢复** `data/app.db`。

## 安全注意事项

- `JWT_SECRET` 由环境变量注入，**禁止入库、禁止写日志**
- 日志中不输出明文口令、口令哈希与 token（见 `backend/src/app/logging.py`）
- 仅收集登录名、昵称与口令哈希，不收集邮箱 / 真实姓名等身份信息

## 手机 / 平板访问（同一局域网）

站点响应式适配手机（≈360–430px）、平板（≈768–1024px）与电脑（≥1280px）；同一账号多设备数据一致，不限制设备数、不互踢。

1. 让服务监听所有网卡：`uvicorn app.main:app --host 0.0.0.0 --port 8000`（Docker 部署已通过端口映射对外）；前端开发态 `npm run dev` 已开启 `host`，可用 `:5173`
2. 取电脑局域网 IP：`ipconfig`（Windows）/ `ip addr`（Linux）
3. 手机 / 平板连同一网络，浏览器打开 `http://<局域网IP>:8000`
4. 打不开多为防火墙拦截：放行 8000（开发态另放行 5173）入站

> 本版仅支持同一网络内访问，无公网部署、域名与 HTTPS；校外远程访问需另行方案。

## 发音服务

发音优先由**服务端 TTS（edge-tts）**合成：单词与整句例句统一音色，结果写入磁盘缓存，不支持浏览器语音合成的设备同样可播放。

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `TTS_VOICE` | `en-US-AriaNeural` | 发音音色（可换 `en-US-GuyNeural` / `en-GB-SoniaNeural` 等） |
| `TTS_RATE` | `-15%` | 语速，`-10%` 为放慢 10%，`-20%` 更慢 |
| `TTS_TIMEOUT_SECONDS` | `8` | 单次合成超时（超时后回退上游） |
| `PRONOUNCE_CACHE_DIR` | `data/cache/pronounce` | 音频缓存目录，可安全清空（按需重建） |

降级链：`edge-tts` → 有道 `dictvoice`（仅单词 / 短短语，整句上游返回 500）→ 接口 404 → 前端浏览器 `speechSynthesis` → 仍不支持时提示「当前浏览器不支持朗读」。

## 常见问题

| 现象 | 排查 |
|---|---|
| 发音总是提示"已使用本地朗读" | 公网不可达或上游无该词；检查 `PRONOUNCE_UPSTREAM_URL` 与超时配置 |
| 测验按钮一直置灰 | 当日单词未全部浏览；在 `/study` 标记完所有单词 |
| 错题不减少 | 符合设计：仅在 `/review` 专项练习答对才移除 |
| 页面空白（生产） | 检查 `STATIC_DIR` 是否指向构建产物目录，且已执行 `npm run build` |
| 手机 / 平板打不开站点 | 服务未监听 `0.0.0.0`、设备不在同一网络，或防火墙未放行端口（见上一节） |
| 手机与电脑数据不一致 | 以服务端数据为准：确认两台设备登录的是同一账号，并刷新页面重新拉取 |
