# Research: 词库循环学习与轮次统计

**Feature**: `003-library-cycle-rounds` | **Date**: 2026-09-29

## 现状结论（代码事实）

| 事实 | 位置 |
|---|---|
| 词库共 **2096** 词 | `backend/seeds/words.txt`（Alembic `002` 幂等 upsert 入库） |
| 取词 = 排除"进过任意 daily_set 的词"，按 `Word.id` 升序 `limit(goal)` | `backend/src/app/services/study_service.py::get_or_create_today_set` |
| 词库耗尽 → 当日集合为空 → `quiz_unlocked=False` → `POST /quiz/daily/start` 抛 `quiz_locked` | `study_service.today_summary`、`quiz_service.start_daily_quiz` |
| 前端空状态兜底"今日暂无待学习单词" | `frontend/src/pages/TodayStudyPage.vue` |
| 当日测验"完成"的判定 = `POST /quiz/daily/finish`（attempt 写 `finished_at`） | `quiz_service.finish_daily_quiz` |
| 已有迁移：`001` 建表、`002` 词表种子、`003` 错题熟练度与错题库 | `backend/alembic/versions/` |

## 决策与理由

### R-001 轮次建模：新增独立 `study_rounds` 表

- **Decision**: 每个账号维护"当前轮"一行记录；不做"单词—轮次"归属明细表。
- **Rationale**: 需求只要求"每轮覆盖词库一次 + 按原顺序 + 统计完成轮数"，不要求查询"某词在哪一轮学过"；独立表可 O(1) 得到当前轮与进度，避免每天对 `daily_set_items` 做全量聚合。
- **Alternatives considered**: ① 从 `daily_set_items` 历史派生轮次 —— 需全表扫描与轮边界推断，且词库更新后无法解释；② 建 `study_round_words` 归属表 —— 多一张 2096×轮数的表，违反章程"简洁（YAGNI）"。

### R-002 每轮每词一次：**游标取词**（不建归属表）

- **Decision**: 轮次记录保存 `cursor_word_id`（下一个待分配单词 id）。每日分配 = `SELECT ... WHERE id >= cursor ORDER BY id LIMIT goal`，分配后推进游标；`cursor > max(Word.id)` 即本轮覆盖完成。
- **Rationale**: 需求已确定"按词库原顺序从头再来"，顺序分配天然等价于"本轮每词恰好一次"，无需额外记录集合；同时兼容词库更新（新词 id 更大会自动纳入当前轮，符合 Assumptions）。
- **Alternatives considered**: 归属表 `NOT IN (...)` 子查询 —— 每轮 2096 行、跨多轮行数线性膨胀，仅换来"可查询历史归属"这一需求外的能力。

### R-003 一轮"完成"的两段式状态机

- **Decision**: 轮次状态 `进行中 → 已覆盖（covered）→ 已完成（completed）`：
  - **已覆盖**：游标越过词库最后一个单词（当日单词已分配完）；
  - **已完成**：已覆盖 **且** 该轮最后一天的今日测验已完成（`finish_daily_quiz` 落 `finished_at`）→ 此时"已完成轮数" +1。
- **Rationale**: 直接对应 FR-004（用户选择"当日测验也完成才算"）；两段式让"学完最后一词但没做测验"这一中间态可被识别与提示。
- **Alternatives considered**: 浏览完即 +1（用户已否决）；把测验完成写入 attempt 后反查（等价但把轮次判定散落到测验模块，故改为：测验模块只发"当日测验完成"信号，轮次模块决定状态迁移）。

### R-004 轮末补记（FR-014）的触发点

- **Decision**: 补记放在 `round_service` 的**轮次读取统一入口**：任何要返回"当前轮 / 轮次进度"的调用（`ensure_open_round`、`progress`）都先执行 `settle_pending_rounds` —— 若存在 **已覆盖但未完成**、且其覆盖日已早于今天的轮次，则以当前时间补 `completed_at`（不伪造测验成绩），随后开启新一轮。`study_service.get_or_create_today_set`（学习页分配）与 `home_service.summary`（首页展示）**都必须经由该入口**。
- **Rationale**: 当日测验机会随日期结束而消失（`daily` attempt 按 `study_date` 定位），不补记会让学生永久卡在无法收尾的一轮里。之所以要求"读取入口"而非"分配入口"：学生次日可能**先看首页再进学习页**，若只在分配入口补记，首页会读到补记前的轮数，与学习页/刷新后结果不一致，直接违反 SC-003（轮次数字准确）与 SC-006（刷新、重新登录、跨设备一致）。放在读取入口后，任何页面、任何时序看到的轮数都一致，且逻辑仍集中在单一函数，可单点测试。
- **Alternatives considered**: ① 仅在 `get_or_create_today_set` 补记（**已否决** —— 首页漏补记，与 SC-006 冲突）；② 允许跨日补答昨日测验 —— 需放开 attempt 跨日约束，改动测验解锁规则，成本高；③ 定时任务扫描 —— 单容器部署下引入调度组件，违反"简洁"。

### R-005 不考虑历史账号（范围排除）

- **Decision**: 迁移 `004` **只建 `study_rounds` 表与索引，不为已有账号回填轮次行**；已有学习历史的账号不在本版范围内，其升级后的行为不做定义与保证。无学习记录的账号在首次访问学习 / 首页时惰性创建 `round_no = 1`。
- **Rationale**: 用户明确"不需要考虑历史账号"；去掉回填逻辑后迁移只剩建表，风险面与测试面最小，符合章程"简洁（YAGNI）"。
- **Alternatives considered**: 回填 `round_no = 1` 并按历史已学词推算游标（已否决 —— 属用户排除范围）；仅回填游标不判定完成（同样否决）。
- **影响**: `quickstart.md` 原"场景 H（老账号回填）"、"data-model.md" 回填规则、`tasks.md` 的回填与迁移测试均已同步移除。

### R-006 接口与展示：扩字段，不加新端点

- **Decision**: 复用现有两个端点，仅扩展响应字段——`GET /home/summary` 增加 `completed_rounds` 与 `current_round`；`GET /study/today` 增加 `round_no` / `round_learned` / `round_total`。前端首页新增"轮次"卡片与大字体建议文案，学习页在进度行显示本轮进度。
- **Rationale**: 无新页面、无新交互，改动面最小；契约变更集中在两处，便于契约测试覆盖。
- **Alternatives considered**: 新增 `GET /study/rounds` 端点 —— 多一次请求与一份契约，收益为零。

### R-007 测试策略（TDD，章程 III / IV）

- **Decision**: 先写失败测试再实现，分三层：
  - **unit**：游标推进、跨轮开启、已覆盖/已完成迁移、补记规则；
  - **contract**：两个端点的响应字段与类型（含 0 轮初始态）；
  - **integration**：真实 SQLite + HTTP 链路跑"词库耗尽 → 次日自动新一轮 → 完成测验 → 已完成 1 轮 → 错题本/历史数据不变"。
- **Rationale**: 轮次与测验的接缝（完成信号 → 轮次 +1）是最易出错处，必须集成测试；游标逻辑纯函数化，单元测试最快。
- **Alternatives considered**: 仅集成测试（慢且难覆盖补记边界）；mock 掉测验服务（章程 IV 禁止用 mock 掩盖接线）。

### R-008 合规自查

- **Decision**: 本功能只新增"学习进度与轮次"（`study_rounds`），不采集身份信息、不采集在线行为、不出站、不共享第三方；按章程"领域合规"第 1–5 条无新增风险，第 6 条（新增字段审查）结论记录于本文件，无需修订章程。
- **Rationale**: 轮次与游标属于既有学习数据的派生统计，非新的个人信息类别。

## 未决项

无。spec 中的 3 项澄清已全部由用户确认并写入 FR-004 / FR-012 / FR-013。
