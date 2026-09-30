# 1+1=2 —— 中考英语单词学习测验与错题本

> 产品名称：**1+1=2**（浏览器标签标题与站内页头统一展示该名称）

面向初中学生的中考英语单词记忆 Web 站点：注册登录 → 设置每日背词目标 → 按目标学习当日单词（含发音）→ 全部浏览后解锁今日测验 → 答错进入错题本 → **错题专项练习答对才移除**。

## 技术栈

- 后端：Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + SQLite（WAL）
- 前端：Vue 3 + Vite + TypeScript + Pinia + Tailwind CSS
- 部署：Docker Compose 单容器（后端托管前端构建产物）

## 三条硬性业务规则

1. 当日单词**未全部浏览**不得开启今日测验（后端 409 `quiz_locked`，前端入口置灰）
2. 今日测验**答对不移除**错题本记录
3. 错题本**唯一**移除途径 = 错题专项练习答对；日期切换 / 重新登录 / 学习新词都不会清空

这三条分别由 `backend/tests/integration/test_quiz_lock.py`、`test_quiz_flow.py::test_correct_answer_in_daily_quiz_never_removes_wrong_word`、`test_wrong_word_persistence.py` + `test_review_flow.py` 守护。

## 本地启动

```bash
# 后端（终端 1）
cd backend
uv sync --extra dev          # 或 pip install -e ".[dev]"
alembic upgrade head         # 建表 + 导入内置词表种子
uvicorn app.main:app --reload --port 8000

# 前端（终端 2）
cd frontend
npm install
npm run dev                  # http://localhost:5173（已配置 /api 代理）
```

生产形态：先 `cd frontend && npm run build`，再启动后端即可，后端会自动托管 `frontend/dist`。

## 手机 / 平板访问（同一局域网）

站点为响应式布局，手机（≈360–430px）、平板（≈768–1024px）、电脑（≥1280px）三档宽度均可完成全流程；同一账号在任意设备上数据一致，不限制设备数、不互踢。

```bash
# 生产形态（推荐）：后端监听所有网卡
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 开发形态：Vite 已开启 host，手机可直接访问 http://<电脑局域网IP>:5173
cd frontend && npm run dev
```

1. 查出电脑的局域网 IP：`ipconfig`（Windows）或 `ip addr`（Linux），如 `192.168.1.23`
2. 手机 / 平板与电脑连**同一个 Wi-Fi**，浏览器打开 `http://192.168.1.23:8000`（开发形态用 `:5173`）
3. 打不开通常是系统防火墙拦截：Windows 需放行 8000 / 5173 端口入站（首次运行会弹窗，选"允许访问"）

> 说明：本版仅支持同一网络内访问，未做公网部署、域名与 HTTPS；校外远程访问需另行方案。

## 测试

```bash
cd backend && uv run --extra dev pytest        # 单元 / 契约 / 集成（真实 SQLite + TestClient）
cd frontend && npm run test                    # Vitest 组件与状态
cd backend && uv run python scripts/validate_word_seed.py   # 词表种子体检
```

## Docker 部署

```bash
cp .env.example .env        # 修改 JWT_SECRET
docker compose up -d --build
# 访问 http://localhost:8000
```

数据与发音缓存持久化在 `./data`（见 `docs/operations.md`）。

## 云服务器部署（脚本 `deploy/deploy.sh`）

适用于 Docker Hub 不可达的云主机：Python venv + systemd 直跑，后端同时托管前端构建产物。

```bash
# 1) 本地打包（排除 node_modules / data / __pycache__）并上传
tar --exclude=__pycache__ --exclude=data -czf deploy.tgz backend/src backend/alembic backend/alembic.ini backend/pyproject.toml backend/seeds frontend/dist deploy
scp deploy.tgz root@<服务器IP>:/opt/

# 2) 服务器上解压并部署（PORT 默认 8010，JWT_SECRET 必填）
ssh root@<服务器IP> "mkdir -p /opt/1plus1 && tar -xzf /opt/deploy.tgz -C /opt/1plus1"
ssh root@<服务器IP> "cd /opt/1plus1 && JWT_SECRET=\$(openssl rand -base64 48) PORT=8010 bash deploy/deploy.sh"
```

脚本执行：venv 装依赖 → 写 `/etc/1plus1.env`（600，含 `JWT_SECRET` / `DB_PATH` / `STATIC_DIR`）→ `alembic upgrade head` → systemd 服务 `1plus1` → `ufw allow <PORT>` → 健康检查。

运维常用：

```bash
systemctl status 1plus1          # 状态
journalctl -u 1plus1 -f          # 日志
systemctl restart 1plus1         # 重启
```

> 云端安全组 / 防火墙需放行服务端口；数据文件在 `/opt/1plus1/data/app.db`。

## 替换 / 扩充词表

词表源文件为 `backend/seeds/words.txt`，统一格式每行一条：

```
单词 | 词性.释义 | 例句
# 例：the | art. 指已提到或易领会到的人或事物 | I have an apple. 我有一个苹果。
# 例：connect | v.(使)连接；与……有联系 | We are waiting for the telephone to be connected. | 我们在等待电话接通。
```

`#` 为注释，`====第N组====` 分组行会被忽略；单词大小写不敏感去重；例句的英文与中文若被 `|` 分隔会自动合并为一条。旧格式（`单词 词性.释义 | 短语1；短语2`）仍可解析。

拿到新词表（如桌面 `aa.txt`）后：

```bash
cd backend
uv run python scripts/normalize_words.py C:\Users\me\Desktop\aa.txt  # 归一为 seeds/words.txt
uv run python scripts/validate_word_seed.py                          # 体检（唯一性 / 条数下限）
uv run python scripts/reset_words.py                                 # 清理旧词表及学习/测验/错题数据（保留账号，自动备份）
uv run alembic downgrade 001 && uv run alembic upgrade head          # 重新导入词表
```

> 只想追加词条、不动已有数据：跳过 `reset_words.py`，直接 `alembic upgrade head`（002 按 `spelling` 幂等 upsert）。

如需新增更多词表版本，复制 `002` 为 `003…` 同样以 upsert 方式导入即可。

## 页面

| 路由 | 页面 |
|---|---|
| `/register` `/login` | 注册 / 登录 |
| `/home` | 首页（进度、每日目标、错题总数） |
| `/settings` | 每日单词目标 |
| `/study` | 今日单词学习（含发音与已浏览标记） |
| `/quiz` | 今日单词测验（需全部浏览解锁） |
| `/wrong-words` | 错题本 |
| `/review` | 错题专项练习 |
