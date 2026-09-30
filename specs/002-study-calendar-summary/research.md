# Research: 学习日历总结

**Feature**: `002-study-calendar-summary` | **Date**: 2026-09-30

目标：在既有 FastAPI + SQLite + Vue 3 栈上新增「总结」页（月历 + 单日明细 + 月度汇总 + 连续天数）。**在线时长已于 2026-09-30 从本功能移除**（见 `spec.md` 变更记录），因此本文件不含任何时长采集方案。

## 既有事实基线（代码勘察结论）

| 事项 | 结论 |
|---|---|
| 时间存储 | 所有 `datetime` 以 **naive UTC** 入库（`models/base.py: utcnow()`）；服务端"当日"按 `settings.timezone = "Asia/Shanghai"` 换算（`study_service.today_date()`） |
| 学习单词数 | `daily_sets`（`user_id`, `study_date`, 唯一约束 `(user_id, study_date)`）⋈ `daily_set_items`（`viewed_at` NULL = 未浏览）。`daily_sets` 一行在打开首页 / 学习页时即生成 |
| 今日测验 | `quiz_attempts`：`kind='daily'` + `study_date` 有值；`total_count` / `correct_count` / `wrong_count`；`finished_at` 非空 = 已完成 |
| 错题本专项 | `quiz_attempts`：`kind='review'`，**`study_date` 恒为 NULL**（只能按时间字段归日）；作答明细在 `quiz_answers`（`is_correct`, `answered_at`） |
| 错题库专项 | `kind='archive'`，同上；`wrong_word_archive` **无任何时间字段**，不能用于按日统计，只能用 `kind='archive'` 的练习轮次 |
| 索引现状 | `quiz_attempts` **无任何索引**；`quiz_answers` 有 `UNIQUE(attempt_id, word_id)`（可作 `attempt_id` 前缀索引）；`daily_sets` 靠唯一约束可走 `(user_id, study_date)` |
| 前端 | 路由 `router/index.ts`（懒加载、`meta.public` 控制免登录）；导航 `components/AppShell.vue` 的 `navItems`；api 封装在 `src/api/*.ts`（`client.ts` 自动带 Bearer） |
| 后端分层 | `api/*.py`（前缀在 `main.py` 统一挂 `/api`）→ `services/*.py` → `models/`；鉴权 `Depends(get_current_user)` |

---

### R-001 汇总方式：实时聚合 vs 落一张 `daily_summaries` 表

- **Decision**: **不新增业务表**，按月 / 按日**实时聚合**既有表；迁移 `005` 只新增查询索引。
- **Rationale**: ① FR-014 要的"长期保留、可回溯"由既有历史数据天然满足（既有表不删历史），不需要再抄一份；② 单账号规模下（<1000 账号、日活 <200、每日至多几十条作答）按月聚合是毫秒级，远快于 SC-001 的 3 秒；③ 物化表会引入"回填历史 + 增量维护 + 与源数据不一致"三类新问题，违反章程 V（简洁 / YAGNI）；④ 不新增表 ⇒ **不新增任何个人信息字段**（见 R-007）。
- **Alternatives considered**: ① 建 `daily_summaries` 表并在学习/测验/练习写入时增量更新 —— 需回填历史账号、需处理并发与补偿，且一旦与源数据漂移难以解释；② 物化视图 —— SQLite 不支持增量物化视图，仍需触发器维护，复杂度同上。

### R-002 各项数据的"归日"口径

- **Decision**: 统一"以既有服务端当日口径为主，行为时刻为辅"：
  - **学习单词数**：按 `daily_sets.study_date` 归属（与每日学习集合同一口径，`viewed_at` 仅用于判断"是否浏览过"）；
  - **今日测验**：按 `quiz_attempts.study_date` 归属（daily 自带该字段）；
  - **两类专项练习**：按 `quiz_answers.answered_at` 换算 Asia/Shanghai 后的日期归属（attempt 的 `study_date` 为 NULL，只能用时刻）。
- **Rationale**: 前两项沿用既有"当日"定义，与学习页、测验页显示的数字必然一致（避免"同一天两个数字"）；专项练习没有日期列，只能按作答时刻，这也正好满足 FR-013 的"跨零点按行为发生时刻归属"。
- **Alternatives considered**: ① 全部按时刻换算 —— 会让"今日测验"与既有 `/quiz` 页按 `study_date` 的结果在跨零点时打架；② 专项练习按 `attempt.finished_at` 归日 —— 与答题明细的归日口径不一致，跨零点时"答题数"与"轮数"可能落在不同日期。

### R-003 专项练习的"轮数 / 答题数 / 答对数 / 答错数"

- **Decision**: 一轮 = 一个 `finished_at` 非空的 attempt。四项数字全部由 **`quiz_answers` 按 `answered_at` 归日**统计：答题数 = `COUNT(*)`；答对 = `SUM(is_correct)`；答错 = `COUNT(*) - 答对`；轮数 = `COUNT(DISTINCT attempt_id)`（该日有作答即计该轮）。`quiz_answers` 有 `UNIQUE(attempt_id, word_id)`，同一题重答以最后一次 `is_correct` 为准，不重复计数。
- **Rationale**: 单一口径（都来自"当天实际作答"），多轮练习天然累加，满足 FR-012（多轮汇总、不互相覆盖）；未答完的 attempt（`finished_at` 为空）若已有作答，其已答部分仍计入当天，符合"不做事后补算、也不抹掉已发生行为"。
- **Alternatives considered**: ① 直接用 attempt 的 `total_count/correct_count/wrong_count` 按 `finished_at` 归日 —— 与答题明细口径不一致（见 R-002）；② 只统计已完成轮 —— 会丢掉"做到一半关掉页面"那天的数据，与 FR-012/Edge Cases 冲突。

### R-004 三级着色与深绿分档

- **Decision**: `level` 三值 —— `gray`（无 `daily_sets` 记录）/ `light`（有 `daily_sets` 记录但当天无学习行为）/ `deep`（当天有学习行为）；`deep` 再按当天学习单词数分 **3 档**（`shade` 1/2/3）：`1–9` → 1、`10–29` → 2、`≥30` → 3。
- **Rationale**: 满足 FR-019"至少三个可辨识层级"；阈值沿用 `spec.md` Assumptions 的示例值，且与每日目标（默认 20 词上下）同量级，视觉上区分度明显。浅绿用"是否生成过当日学习集合"判定（打开首页 / 学习页即生成），**不新增任何采集字段**。
- **Alternatives considered**: ① 按"学习词数 / 当日目标"比例分档 —— 目标会变，同一天不同时间看颜色会变，违反 SC-004；② 按在线时长分档 —— 指标已取消。

### R-005 历史账号与历史数据

- **Decision**: **无需回填、无需排除历史账号**。与 003 不同，002 只读取既有数据做聚合，老账号升级后立刻能看到自己过去每天的日历着色与明细。
- **Rationale**: 数据源是 `daily_sets` / `quiz_attempts` / `quiz_answers` 这些 001 就在写的表，历史天然存在；聚合是只读的，不存在"升级后才产生的字段"。
- **Alternatives considered**: 无（不存在需要回填的内容）。

### R-006 接口设计

- **Decision**: 新增一个域 `summary`，两个只读端点：
  - `GET /api/summary/month?month=YYYY-MM` —— 该月每天的 `date/level/shade/learned_count` + `month_total` + `streak_days` + `today`；
  - `GET /api/summary/day?date=YYYY-MM-DD` —— 当天四项明细 + `has_record`。
  无记录 / 未来日期 / 注册前日期统一返回 `200` + `has_record=false` 且各项为 0（由前端给出"当天没有学习记录"提示），**不返回 404**（避免把"无数据"当错误处理）。
- **Rationale**: 月接口一次给出整月（日历 + 月度汇总 + 连续天数），满足 SC-001/SC-008；日接口按需拉取，满足 SC-002 的 1 秒；两个端点都只读，无副作用。
- **Alternatives considered**: ① 月接口直接带上 30 天的完整明细 —— 首屏 payload 变大且多数日期用不上，违反简洁；② 单个端点 `?month=&date=` 二合一 —— 参数耦合、语义不清。

### R-007 合规（章程「领域合规」第 6 条）

- **Decision**: **不触发**章程第 6 条的前置审查 —— 本功能**不新增任何个人信息字段、不新增采集行为、不上报任何数据**；新增的仅是数据库**索引**（迁移 `005`）。结论已记录在 `spec.md`「合规结论」与 `checklists/requirements.md`。
- **Rationale**: 唯一曾被质疑的"在线时长"已整体移除；浅绿改用既有痕迹（当日学习集合是否存在）判定。索引属于物理存储结构，不改变收集范围。
- **Alternatives considered**: ① 为"是否打开过"新增 `last_active_date` 字段 —— 属新增个人信息采集，需走章程修订 + 审查，已否决（见 `spec.md` Session 2026-09-30）。

### R-008 索引与性能

- **Decision**: 迁移 `005` 新增 3 个索引：`quiz_attempts(user_id, kind, study_date)`、`quiz_attempts(user_id, finished_at)`、`quiz_answers(answered_at)`。查询按月范围一次性 `GROUP BY`，**禁止按天循环查询**（N+1）。
- **Rationale**: 既有 `quiz_attempts` 无索引，按月聚合会全表扫描；单账号数据量虽小，但索引成本极低且为只读查询，符合"规模化前先消除明显扫描"（数据规模 <1000 账号，索引后仍为毫秒级，SC-001 的 3 秒目标有充分余量）。
- **Alternatives considered**: 不加索引（全表扫描）—— 当前规模可接受，但会随使用时长线性劣化，且成本几乎为零，故不采纳。

### R-009 测试策略

- **Decision**: 三层覆盖 —— unit（`summary_service` 聚合口径与着色/连续天数规则）、contract（两个端点的字段集合、无记录日期的 `has_record=false`、跨月参数）、integration（真实 SQLite + HTTP：学习 → 浏览 → 测验 → 两类专项练习 → 查月/日接口，数字与实际行为一致；换设备/重新登录一致）。**不使用 mock** 掩盖聚合 SQL。
- **Rationale**: 章程 III（测试先行）、IV（集成覆盖接缝）；本功能的主要风险是"聚合口径与页面实际行为不一致"，只有集成测试能证明。
- **Alternatives considered**: 只写单元测试 —— 无法证明 SQL 归日与接口接线正确，违反章程 IV。

### R-010 前端落地方式

- **Decision**: 新增 `frontend/src/pages/SummaryPage.vue`（路由 `/summary`）+ `frontend/src/api/summary.ts`，并在 `AppShell.vue` 的 `navItems` 增加入口；日历用原生 table/div 网格 + Tailwind 实现，**不引入任何日历组件库**。
- **Rationale**: 与既有页面惯例一致（懒加载路由、api 封装、AppShell 导航）；月历只需 7×6 网格与三种底色，引入组件库属于"为小需求引入依赖"，违反附加约束「依赖引入需论证」。
- **Alternatives considered**: 引入 FullCalendar 等日历库 —— 体积大、需定制主题，收益不抵成本，已否决。
