# Research: 中考英语单词学习测验与错题本

**Feature**: 001-word-study-quiz | **Date**: 2026-09-28

Technical Context 中无 NEEDS CLARIFICATION 项（技术栈已由用户确认：Python + FastAPI + SQLAlchemy + Alembic + SQLite，Vue 3 + Vite，Docker Compose）。本节记录设计阶段的关键决策、理由与被否决的备选方案。

---

## R-001 词表数据如何内置与导入

**Decision**: 词表以 `backend/seeds/words.txt`（统一格式 `单词 词性.释义 | 短语1；短语2`，解析见 `app/seed_words.py`）随代码入库；由独立 Alembic 迁移 `002` 一次性导入 `words` 表；以 `spelling` 为唯一键做幂等 upsert。

**Rationale**: 与代码同版本管理，部署即具备数据，无需外部数据服务（FR-011）；独立迁移使"替换词表"变成"改种子文件 + 新增一条 upsert 迁移"，不动用户表，符合"替换词表不影响学习进度与错题本"。

**Alternatives considered**:
- 启动时检测空表再导入 —— 与应用启动耦合、难以追踪版本变更，否决
- 运行时调用在线词典 API 拉词 —— 违反 FR-011（不依赖外部词库服务），否决
- CSV 种子 —— 中文与逗号转义易出错，选 JSON

---

## R-002 口令存储方式

**Decision**: `passlib[bcrypt]` 哈希（cost 12），仅保存哈希；登录校验用 `verify`；任何响应与日志中都不得输出口令。

**Rationale**: 满足 FR-005（不保存明文）与章程数据保护要求；bcrypt 自带盐与抗 GPU 暴力破解特性，是 Web 场景通行做法。

**Alternatives considered**:
- Argon2id —— 更强，但需额外原生依赖，当前规模不必要，列为未来升级项
- 自行 SHA256 + 盐 —— 不满足抗暴力破解要求，否决

---

## R-003 登录态与会话方案

**Decision**: 无状态 JWT（HS256），登录后前端保存 token 并在请求头 `Authorization: Bearer <token>` 携带；有效期 7 天；密钥由环境变量 `JWT_SECRET` 注入；登出由前端清除 token（服务端无需状态）。

**Rationale**: SQLite 单容器部署，无需会话表（简洁原则 V）；与前后端分离形态匹配；未登录访问受限接口统一返回 401，路由守卫据此跳转登录页（FR-004）。

**Alternatives considered**:
- 服务端会话表 —— 需额外表与清理机制，收益不抵复杂度，否决
- HttpOnly Cookie —— 更安全但需处理 CSRF 与跨域部署；本版前后端同源托管，Bearer 方案足够，CSRF 风险因同源且无 Cookie 自动携带而天然较低

---

## R-004 单词发音的获取与降级

**Decision**: 后端提供 `GET /api/pronounce/{word}` 代理第三方公共发音接口（如有道 `dictvoice` 一类公开发音地址）；服务端设置 2 秒超时；成功则把音频字节缓存到磁盘目录（按 `word` 命名，命中缓存直接返回）；接口无结果 / 超时 / 异常时返回明确错误码，前端检测到即调用 `speechSynthesis`（`lang=en-US`）朗读。

**Rationale**: 用户不提供本地 mp3（Clarifications Q2），且部署环境可访问公网（Q3）；服务端代理可统一超时、缓存与失败处理，避免前端直连第三方带来的跨域与不可控失败；降级路径满足 FR-016 与 SC-006。

**Alternatives considered**:
- 前端直连第三方发音地址 —— 跨域与失败不可控，否决
- 商业云 TTS —— 需密钥与额度，本版不引入（已在 Clarifications 排除）
- 构建期批量下载音频入库 —— 版权合规风险，已否决

---

## R-005 SQLite 并发与连接策略

**Decision**: SQLite 开启 WAL 模式、`busy_timeout=5000`；uvicorn 单进程单 worker；写操作集中在短事务（标记浏览、记录作答、增删错题）；每日冷启动不需要额外连接管理。

**Rationale**: 单人学习场景写入频率极低（每用户每天数十次），WAL + 单进程完全消除写锁冲突（SC-008 数据零丢失）；避免多 worker 争抢单文件写锁。

**Alternatives considered**:
- PostgreSQL —— 用户已选择 SQLite（部署最简），否决
- 多 worker + 共享 SQLite —— 写锁竞争与复杂度上升，收益为零，否决

---

## R-006 "当日"边界与每日单词分配

**Decision**: 以服务端统一时区（Asia/Shanghai, UTC+8）计算 `study_date`；`daily_sets` 以 `(user_id, study_date)` 唯一；用户首次访问今日学习页时，按当前每日目标从**未学习过**的单词中按 `words.id` 升序取词生成集合与明细；当日重复访问返回同一集合；目标变更不影响当日集合（次日生效）；未学单词不足时按剩余数量分配并提示词库已学完。

**Rationale**: 直接对应 FR-010 / FR-014 / FR-020 与 Assumptions（UTC+8、只分配未学单词）；唯一约束天然防止重复生成，也解释了"目标改小后已浏览数 > 目标数"的边界（集合不变）。

**Alternatives considered**:
- 按用户设备时区 —— 需存时区配置且跨设备不一致，已在 Assumptions 排除
- 每日 0 点批量预生成 —— 需要调度任务，首次访问生成更简洁（YAGNI）

---

## R-007 测验出题与干扰项生成

**Decision**: 题量 = 当日单词数，每词一题；每题随机选题型 A（给英文选中文）或 B（给中文选英文）；干扰项从**词库**随机取 3 个不同的其他单词的同类型文本；生成时校验"干扰项文本 ≠ 正确文本"且选项去重；正确答案不随题目下发，提交后返回 `correct` 与 `correct_index` 并给出反馈。

**Rationale**: 满足 FR-022~FR-024、FR-027；答案不下发避免前端泄题；文本去重避免"两个相同选项"的边界问题（Edge Cases）。

**Alternatives considered**:
- 干扰项取自当日单词 —— 选项过于集中、易猜，否决（取全词库更合理）
- 服务端保存题目快照 —— 增加表与复杂度，本版题目可即时生成，否决（错题记录只依赖 word_id）

---

## R-008 错题本删除规则的服务层隔离（核心风险点）

**Decision**: 错题本写操作只暴露两个函数，且**删除只存在于其中一个**：
- `record_daily_quiz_answer(...)`：答错 → 新增错题（`added_at = now`，唯一键冲突则忽略，保留首次时间）；答对 → **不执行任何删除**
- `record_review_answer(...)`：答错 → 保持不变（不改 `added_at`）；答对 → 删除该错题记录

`wrong_words` 以 `(user_id, word_id)` 唯一；所有其他路径（日期切换、登录、学新词、改设置）均无任何删除语句。

**Rationale**: 把"唯一移除条件"固化为代码结构（FR-026 / FR-031），配合定向测试（今日测验答对后错题数不变、专项练习答对后错题数减一）形成双重保障；SC-003 / SC-004 直接以这两个函数的行为为判据。

**Alternatives considered**:
- 统一答题函数 + 标志位区分来源 —— 一处 if 决定删除与否，易被后续需求误改，否决
- 错题本保留"移除时间"软删除 —— 增加状态复杂度，PRD 要求"从错题本删除"，否决

---

## R-009 迁移与种子数据组织

**Decision**: Alembic `001` 建立全部业务表与索引；`002` 读取 `seeds/words.txt` 导入词表（幂等 upsert，按 `spelling`）；后续替换词表新增 `003…` 同样以 upsert 方式执行，不删除用户数据。

**Rationale**: 迁移即版本化数据变更，部署 `alembic upgrade head` 即得完整可用系统；词表导入与建表分离，便于替换与回滚。

**Alternatives considered**: 单条迁移同时建表与导词 —— 替换词表时难以复用，否决

---

## R-010 前端响应式与页面结构

**Decision**: Vue 3 + Vite + TypeScript + vue-router + Pinia；样式用 Tailwind CSS 断点（`sm/md/lg`）实现单列→多列自适应；关键交互（发音按钮、标记已浏览、选项点击）触控区域 ≥ 44px；360 / 768 / 1440 三个视口纳入验收（SC-005）。

**Rationale**: 满足 FR-042 与 US7；Tailwind 断点可低成本保证窄屏无横向滚动。

**Alternatives considered**:
- Jinja2 服务端模板 —— 用户已选择 Vue 3 方案，否决
- 自研 CSS 媒体查询 —— 维护成本高，Tailwind 已在依赖清单中论证

---

## R-011 测试策略与关键用例

**Decision**: 后端 pytest 分三层——
- `tests/unit`：口令哈希、JWT、"全部浏览 → 解锁"判定、干扰项去重、UTC+8 日期计算
- `tests/contract`：按 `contracts/api.md` 校验状态码、字段结构与错误码
- `tests/integration`（真实 SQLite 文件 + TestClient）：注册登录、设置目标、学习浏览、测验锁定的 409、答错入本、答对不删、专项答对删除、跨日与重新登录错题数不变、发音代理失败降级

前端 Vitest：组件渲染与答题交互、路由守卫在未登录时跳转。

**Rationale**: 对应章程 III/IV；三条硬性规则在集成层以真实链路验证，避免 mock 掩盖接线错误。

**Alternatives considered**: 仅单元测试 —— 无法覆盖"学习→测验→错题本"接缝，否决

---

## R-012 依赖清单与必要性说明

**Decision** 与理由：

| 依赖 | 必要性 |
|---|---|
| fastapi / uvicorn | Web 框架与 ASGI 服务器，提供 REST 接口与静态资源托管 |
| SQLAlchemy 2.x / Alembic | ORM 与版本化迁移（含词表种子导入） |
| pydantic / pydantic-settings | 请求校验与配置注入（JWT_SECRET、DB 路径、发音超时） |
| passlib[bcrypt] | 口令不可逆哈希（FR-005） |
| PyJWT | 无状态登录态签发与校验（FR-003/FR-004） |
| httpx | 服务端代理发音接口并控制超时（FR-016） |
| pytest / pytest-cov / httpx(TestClient) | 单元 / 契约 / 集成测试（章程 III/IV） |
| vue / vue-router / pinia | 8 个页面路由与全局状态 |
| vite / typescript | 前端构建与类型安全 |
| tailwindcss | 响应式样式断点（FR-042） |
| vitest / @vue/test-utils | 前端组件与交互测试 |

**Alternatives considered**: Django 全栈框架 —— 本项目为 SPA + JSON API，FastAPI 更轻且与既有项目一致；Prisma/TypeORM 等 —— 与 Python 后端不匹配。

---

## R-013 部署形态

**Decision**: 多阶段 Dockerfile（Node 构建前端 → 产物拷入 Python 运行镜像 → uvicorn 单进程）；`docker-compose.yml` 单服务，挂载 `./data:/app/data`（SQLite 文件 + 发音缓存）；对外暴露一个端口；前端产物由后端静态托管，避免额外 nginx 容器。

**Rationale**: SQLite 单文件无需数据库容器；单服务部署最简（章程 V 简洁原则）；卷挂载保证数据持久化（SC-008）。

**Alternatives considered**: nginx + 后端双容器 —— 增加编排与配置成本，本版无此必要，否决
