# Tasks: 学习日历总结

**Input**: Design documents from `/specs/002-study-calendar-summary/`

**Prerequisites**: plan.md（技术栈与结构）、spec.md（5 个 User Story；**在线时长已于 2026-09-30 移除**）、research.md（R-001–R-010）、data-model.md（派生汇总口径与迁移 `005` 索引）、contracts/api.md（2 个只读端点）、quickstart.md（场景 A–F）

**Tests**: **包含测试任务** —— 依据章程 III（测试先行不可协商）、IV（集成测试覆盖关键接缝）与 plan.md。每个 Story 阶段**先写失败用例并确认其失败**，再实现。

**Organization**: 按 User Story 分阶段；Setup / Foundational / Polish 阶段无 Story 标签。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 所属 User Story（US1–US5）
- 每条任务均给出**确切文件路径**

## Path Conventions

- 后端：`backend/src/app/{schemas,services,api}/…`、`backend/tests/{unit,contract,integration}/…`、`backend/alembic/versions/…`、`backend/scripts/…`
- 前端：`frontend/src/{api,pages,components,router}/…`
- 与 plan.md「Project Structure」一致（Web application 结构）

---

## Phase 1: Setup

**Purpose**: 确认改造基线与造数工具（项目骨架与依赖已存在，本次**不新增依赖**）

- [X] T001 确认改造基线：在 `backend/` 下执行 `alembic current`（应为 `004 (head)`，即 003 的 `study_rounds`）与 `pytest -q`（全绿），把输出记录到本文件末尾的验证记录；不通过则先修复再继续
- [X] T002 [P] Create `backend/scripts/seed_summary_history.py`: 本地造数脚本 —— 为指定账号生成最近 N 天的历史行为（`--user`、`--days`，默认 30；含"有学习""只打开未学""完全无记录"三类日期，以及今日测验与两类专项练习记录）；**只新增既有表的数据、不删除任何数据**，按日期幂等；仅供本地验证，不进 Docker 镜像

---

## Phase 2: Foundational（阻塞所有 User Story）

**Purpose**: 查询索引、响应模型与聚合服务 —— 所有 Story 的共同前置

**⚠️ CRITICAL**: 该阶段未完成前不得开始任何 User Story

- [X] T003 Create `backend/alembic/versions/005_summary_query_indexes.py`（`revision="005"`, `down_revision="004"`）：**仅**创建 3 个索引 —— `ix_quiz_attempts_user_kind_date (user_id, kind, study_date)`、`ix_quiz_attempts_user_finished (user_id, finished_at)`、`ix_quiz_answers_answered_at (answered_at)`；`downgrade` 删除这 3 个索引；**不建表、不改字段、不回填数据**；**不使用** `sqlite_where`（避免 003 那个传裸字符串导致索引静默丢失的坑）
- [X] T004 [P] Create `backend/tests/unit/test_summary_indexes.py`: **先写失败用例** —— 迁移 `005` 的 3 个索引真实存在于 `sqlite_master`（护栏，防"索引静默丢失"重演）
- [X] T005 [P] Create `backend/src/app/schemas/summary.py`: `MonthSummary{month,today,days:list[CalendarDay],month_total:MonthTotal,streak_days:int}`、`CalendarDay{date,level,shade,learned_count}`（`level ∈ gray|light|deep`、`shade ∈ 0..3`）、`DaySummary{date,has_record,learned_count,quiz:PracticeStat,review_practice:PracticeStat,archive_practice:PracticeStat}`、`PracticeStat{rounds,answered,correct,wrong}`（今日测验另含 `completed: bool`）、`MonthTotal{learned_words,quiz,review_practice,archive_practice,active_days}`；**不含任何在线时长字段**
- [X] T006 [P] Create `backend/tests/unit/test_summary_service.py`: **先写失败用例** —— ① 学习单词数 = `daily_sets.study_date` 下 `viewed_at` 非空的条目数；② 今日测验按 `kind='daily' AND study_date` 取 `total/correct/wrong`；③ 两类专项练习按 `quiz_answers.answered_at` 归日（轮数 = `COUNT(DISTINCT attempt_id)`，对/错由 `is_correct`）；④ 着色：无 `daily_sets` = `gray`、有集合无学习 = `light`、有学习 = `deep`；⑤ 分档 `1–9→1`、`10–29→2`、`≥30→3`；⑥ 连续天数：当天未学不归零、中断一天重算、无活动为 0；⑦ 月度总计 = 各日之和；⑧ **跨零点**：造一条 23:5x 的专项练习作答（跨过零点）→ 作答数按 `quiz_answers.answered_at` 落在各自日期，学习与今日测验按 `study_date` 归属，不出现"同一天两套数字"（FR-013 / research R-002）
- [X] T007 Create `backend/src/app/services/summary_service.py`: 单一职责 —— `month_summary(db,user_id,month)`（**按月一次性 `GROUP BY` 聚合，禁止按天循环查询**）与 `day_summary(db,user_id,date)`；按 research R-002 的归日口径（学习 / 测验走 `study_date`，专项练习走 `answered_at` 换算 Asia/Shanghai）；着色与分档按 research R-004；连续天数按 data-model「连续学习天数」口径；**只读**，不写入 / 不修改 / 不删除任何既有数据；关键查询写结构化日志（含耗时）

**Checkpoint**: 索引 + 响应模型 + 聚合服务可用，单元测试转绿；此时**端点尚未暴露**

---

## Phase 3: User Story 1 - 学习日历总览 (Priority: P1) 🎯 MVP

**Goal**: 「总结」页显示当月月历，按当天活动分灰 / 浅绿 / 深绿（深绿按学习量分档），默认当前月，可切换月份，「今天」有标识

**Independent Test**: 用 T002 造数（含三类日期）→ 打开总结页 → 学过的是深绿、只打开过的是浅绿、其余灰色 → 切换上/下月正常；单独交付即构成"学习打卡视图"

### Tests for User Story 1 ⚠️（先写，确认 FAIL）

- [X] T008 [P] [US1] Create `backend/tests/contract/test_summary_contract.py`: 契约测试 —— `GET /api/summary/month` 返回字段集合与契约一致（`month/today/days/month_total/streak_days`）、`days` 长度 = 该月天数且按日期升序、`level` 与 `shade` 取值合法、`learned_count` 为整数；`month` 缺省 = 当前月；`month` 格式非法 → `400 invalid_month`
- [X] T009 [P] [US1] Create `backend/tests/integration/test_summary_flow.py`: 真实 SQLite + HTTP 链路 —— 注册 → 学习 → 浏览 N 个词 → 完成今日测验 → 查 `/summary/month`：该日 `level=deep`、`learned_count=N`；只打开首页未学的另一天为 `light`；从未打开过的日期为 `gray`；并断言"当天**只做专项练习、未学新单词**"的日期 `learned_count=0` 但 `level=deep`（spec Edge Cases）

### Implementation for User Story 1

- [X] T010 [US1] Create `backend/src/app/api/summary.py`: `GET /summary/month`（`APIRouter(prefix="/summary")`），参数校验后委托 `summary_service.month_summary`，`response_model=MonthSummary`；鉴权用既有 `Depends(get_current_user)`；无 `try/except` 吞错
- [X] T011 [US1] Update `backend/src/app/main.py`: 注册 `summary` 路由（与既有路由一同挂 `/api` 前缀），不影响其它路由
- [X] T012 [P] [US1] Create `frontend/src/api/summary.ts`: 封装 `getMonthSummary(month?)` 与 `getDaySummary(date)`（复用 `client.ts` 的 `get`，自动带 Bearer）
- [X] T013 [P] [US1] Update `frontend/src/router/index.ts`: 注册 `/summary` 懒加载路由（`component: () => import('@/pages/SummaryPage.vue')`，**不加** `meta.public`）
- [X] T014 [P] [US1] Update `frontend/src/components/AppShell.vue`: `navItems` 增加「总结」入口（path/label/icon 与既有项同构）
- [X] T015 [US1] Create `frontend/src/pages/SummaryPage.vue`: 月历网格 **7 列、周一为第一列**（用原生 div/table + Tailwind，**不引入日历组件库**）；按 `level` 渲染灰 / 浅绿 / 深绿，深绿按 `shade` 三档加深；`today` 加可辨识标识；上一月 / 下一月切换

**Checkpoint**: US1 完成 —— 日历可看、可切换月份；可单独交付

---

## Phase 4: User Story 2 - 查看某天的学习明细 (Priority: P1)

**Goal**: 点击浅绿 / 深绿日期，显示当天四项数据：学习单词数、今日测验答对 / 答错（含正确率）、错题本专项练习、错题库专项练习；**不含在线时长**

**Independent Test**: 在造数出的某天（学习 + 今日测验 + 两类专项练习）点击该日期 → 四项数字与实际行为一致；当天只做了专项练习时学习单词数为 0 但日期仍为深绿

### Tests for User Story 2 ⚠️（先写，确认 FAIL）

- [X] T016 [P] [US2] Extend `backend/tests/contract/test_summary_contract.py`: `GET /api/summary/day` 返回字段集合与契约一致（`date/has_record/learned_count/quiz/review_practice/archive_practice`）；**响应中不存在任何在线时长字段**；`date` 格式非法 → `400 invalid_date`
- [X] T017 [P] [US2] Extend `backend/tests/integration/test_summary_flow.py`: 某天完成学习 N 词 + 今日测验（对 c / 错 w）+ 错题本专项 1 轮 + 错题库专项 1 轮 → `/summary/day` 的四项数字与实际一致；同一天做**多轮**专项练习时数字累加而非覆盖（FR-012）；并加一条**跨零点**用例：23:5x 完成今日测验 / 专项练习 → `/summary/day` 在两天分别显示各自的数字（FR-013 / research R-002）

### Implementation for User Story 2

- [X] T018 [US2] Update `backend/src/app/api/summary.py`: 增加 `GET /summary/day`（`response_model=DaySummary`），委托 `summary_service.day_summary`；无记录时返回 `200` + `has_record=false` 且各项为 0（**不返回 404**）
- [X] T019 [US2] Update `frontend/src/pages/SummaryPage.vue`: 点击日期拉取并渲染明细面板 —— 学习单词数、今日测验（答对 / 答错 / 正确率）、错题本专项（轮数 / 答题 / 对 / 错）、错题库专项（同前）；无数据项显示 0 或"未进行"（FR-011）

**Checkpoint**: US1 + US2 完整闭环 —— 从"哪天学过"到"那天学得怎么样"；可作为 MVP 交付

---

## Phase 5: User Story 3 - 灰色日期与未来日期不可查看 (Priority: P2)

**Goal**: 点击灰色日期（无活动）或未来日期时给出明确"当天没有学习记录"提示，不空白、不报错

**Independent Test**: 点击一个从未使用过的过去日期与一个未来日期 → 均得到明确"无记录"提示

- [X] T020 [P] [US3] Extend `backend/tests/contract/test_summary_contract.py`: 未来日期、注册前日期、无任何活动的过去日期 → 均 `200` + `has_record=false` + 各项为 0（不是 404、不是错误码）
- [X] T021 [US3] Update `frontend/src/pages/SummaryPage.vue`: 灰色 / 未来日期点击时显示「当天没有学习记录」提示（`has_record=false` 时），不显示空白明细面板；**兜底**：接口异常或字段缺失时给出可理解的中文提示，不出现空白块或英文错误堆栈（spec Edge Cases）

**Checkpoint**: US3 完成 —— 边界体验闭环

---

## Phase 6: User Story 4 - 当月总计与连续学习天数 (Priority: P2)

**Goal**: 总结页显示当月汇总（总学习词数、今日测验、两类专项练习、有活动天数）与连续学习天数；切换月份时随之变化

**Independent Test**: 造出连续多天数据 → 月度总计 = 逐日之和 → 今天未学仍显示连续天数 → 中断一天后重新计数 → 无活动月份各项为 0

- [X] T022 [P] [US4] Extend `backend/tests/unit/test_summary_service.py`: 月度总计各字段 = 该月各日明细之和（SC-008）；连续天数三种情形（当天未学取最近连续段不归零 / 中断一天重算 / 无活动为 0）；切换月份时 `month_total` 随之变化
- [X] T023 [US4] Update `frontend/src/pages/SummaryPage.vue`: 月度汇总面板（总学习词数、今日测验答题 / 对 / 错、错题本专项、错题库专项、有活动天数）与「连续学习 N 天」；切月时同步刷新

**Checkpoint**: US4 完成 —— "这一个月坚持得怎么样"可量化

---

## Phase 7: User Story 5 - 历史长期可回溯 (Priority: P3)

**Goal**: 换日、刷新、重新登录、换设备后，历史任意有活动日期的着色与明细仍一致（只读聚合，历史天然保留）

**Independent Test**: 造上月数据 → 逐月回看 → 刷新 / 重新登录 / 换设备（新 token）后结果完全一致

- [X] T024 [P] [US5] Extend `backend/tests/integration/test_summary_flow.py`（**同时闭环 US1 验收 6 的「重新登录 / 跨设备一致」**）: 造出上个月若干天数据 → 查上月月历与逐日明细 → **重新登录（新 token）**后再查，着色、明细、月度总计、连续天数全部一致（FR-014 / SC-004）；同一天多时段使用合并为一份汇总

- [X] T031 [P] [US5] Extend `backend/tests/integration/test_summary_flow.py`: **跨账号隔离断言** —— 注册 A / B 两个账号并各自造出不同的历史数据 → 用 A 的 token 查 `/summary/month` 与 `/summary/day`，返回的日历与明细**只含 A 的数据**（与 B 完全不一致），用 B 的 token 各自只见自己的；响应中不含任何他人 `user_id` 或跨账号字段（FR-016 / SC-007）

**Checkpoint**: 全部 User Story 可独立工作

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 前端适配、性能、端到端验证与回归标注

- [X] T025 [P] 前端视口检查：360 / 768 / 1440 三档下总结页排版（月历不溢出、无横向滚动、明细与月度面板可读）——需在浏览器中人工复核（本环境无浏览器自动化）
- [X] T026 [P] 性能抽样（SC-001 / SC-002）：`GET /api/summary/month` 与 `GET /api/summary/day` 各连续请求 10 次，记录 p95 并确认 < 300ms（plan Performance Goals）；确认按月一次性聚合（无按天循环查询）。**口径**：300ms 指**接口响应耗时**；SC-001 的 3 秒（月历）与 SC-002 的 1 秒（明细）是页面感知耗时，由 T025 / T027 人工复核
- [X] T027 按 `specs/002-study-calendar-summary/quickstart.md` 跑通场景 A–F（用 T002 造数），记录实际结果
- [X] T028 [P] Update `CHANGELOG.md`: 记录「总结」页（月历 / 单日明细 / 月度汇总 / 连续天数）、新增 `/api/summary/*`、迁移 `005`（仅索引），并注明「在线时长」未实施（已按 2026-09-30 决策移除）；并写明**审计结论**：本功能所有汇总数据仅在本人鉴权下返回（端点不接受 `user_id`，取当前登录用户），无新增出站请求、无第三方共享、无导出 / 分享能力（FR-018）
- [X] T029 最终冒烟：`cd backend && pytest -q` 全绿（含 001 / 003 既有测试与 002 新增）+ 前端 `npm run build` 通过
- [X] T030 [P] 回归标注：在 `specs/003-library-cycle-rounds/tasks.md` 验证记录中标注其 US4 验收 3「学习日历总结的历史日期着色」**已由 002 闭环回归**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**：无依赖，立即开始（T001 是 T003 的前置：确认当前 head 为 `004`）
- **Foundational (Phase 2)**：依赖 Setup；**阻塞所有 User Story**（T003 → T004 护栏 → T005 → T006 测试先行 → T007 实现）
- **US1 (Phase 3)**：依赖 Foundational
- **US2 (Phase 4)**：依赖 Foundational + US1 的页面骨架；端到端验证需 US1 的月历已能点击
- **US3 / US4 / US5 (Phase 5–7)**：依赖 Foundational，可与 US1/US2 并行开发（不同文件）
- **Polish (Phase 8)**：依赖上述 Story 完成

### User Story Dependencies

- **US1（P1）**：Foundational 后即可开始，不依赖其他 Story
- **US2（P1）**：需 US1 的月历页面承载明细面板（同文件 `SummaryPage.vue`，故串行）
- **US3（P2）**：Foundational 后即可开始；与 US2 同文件，排在 US2 之后避免冲突
- **US4（P2）**：依赖 `summary_service` 的月度/连续天数聚合（Foundational）
- **US5（P3）**：回归性质，需上述数据链路可用

### Within Each User Story

- 测试先行：先写用例 → 确认 FAIL → 再实现 → 转 PASS
- 顺序：schema / service → 接口 → 前端 → 集成
- 每个 Story 结束停在 Checkpoint 独立验收

### Parallel Opportunities

- Phase 1：T002 与 T001 可并行
- Phase 2：T004 与 T005 可并行；T006 与 T007 串行（测试先行）
- Phase 3：T012 / T013 / T014 可并行（三个不同前端文件）；T008 与 T009 可并行编写
- Phase 4–7：T016 与 T017 可并行；T020 / T022 / T024 / T031 可并行
- Phase 8：T025 / T026 / T028 / T030 可并行

---

## Parallel Example: User Story 1

```text
# 后端契约测试与集成测试可同时开工（不同文件）：
Task: "T008 [P] [US1] Contract test for /api/summary/month in backend/tests/contract/test_summary_contract.py"
Task: "T009 [P] [US1] Integration test in backend/tests/integration/test_summary_flow.py"

# 前端三个不同文件可并行：
Task: "T012 [P] [US1] Create frontend/src/api/summary.ts"
Task: "T013 [P] [US1] Register /summary route in frontend/src/router/index.ts"
Task: "T014 [P] [US1] Add nav item in frontend/src/components/AppShell.vue"

# 串行（同一文件 / 依赖）：
Task: "T010 [US1] Create backend/src/app/api/summary.py"
  → Task: "T011 [US1] Register router in backend/src/app/main.py"
  → Task: "T015 [US1] Create frontend/src/pages/SummaryPage.vue"
```

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. Phase 1 Setup → 2. Phase 2 Foundational（阻塞项，必须完成）→ 3. Phase 3 US1 → **STOP**：月历三级着色可用，即"哪天学过"一眼可见 → 可先行验证

### Incremental Delivery

1. Setup + Foundational → 索引、schema、聚合服务就绪
2. US1 → 月历着色（打卡视图）→ 可交付
3. US2 → 单日四项明细 → 用户点名要的核心数据完成 → 可交付
4. US3 → 无记录日期的边界提示
5. US4 → 月度汇总与连续天数（激励价值）
6. US5 → 历史回溯与跨设备一致（回归）
7. Polish → 视口、性能、端到端验证、CHANGELOG 与 003 回归标注

### Notes

- 本次**不新增第三方依赖**（不引入日历组件库，日历用 Tailwind 网格实现；research R-010）
- **在线时长已移除**：任何任务都不得引入时长字段、上报接口或展示（US2 明细为四项）
- **只读聚合**：`summary_service` 不得写入、修改或删除任何既有数据；不建汇总表（research R-001）
- **不新增个人信息字段**：浅绿复用既有 `daily_sets` 痕迹；迁移 `005` 只加索引（research R-007），因此不触发章程「领域合规 · 第 6 条」审查
- 跨零点归属：学习 / 测验走 `study_date`，专项练习走 `quiz_answers.answered_at` 换算 Asia/Shanghai（research R-002）—— 这是本功能最易错处，必须集成测试（禁用 mock）
- 验证记录：见本文件末尾「验证记录（实施阶段）」

---

## 验证记录（实施阶段）

### T001 基线（实施前）

- `alembic current` → 实施前 `004 (head)`；迁移 `005` 执行后 `005 (head)`
- `pytest -q` → **163 passed**（001 / 003 既有全绿；002 新增 24 个后为 187）
- `checklists/requirements.md`：**16 / 16 PASS**（无未勾选项，门禁通过）
- ignore 文件：根 `.gitignore` / `.dockerignore` 已覆盖 Python 与 Node 的通用项，本次无新增运行时产物 → 未改动

### 002 新增用例（24 个）

| 层 | 文件 | 用例数 |
|---|---|---|
| unit | `tests/unit/test_summary_service.py`（聚合口径 / 着色 / 分档 / 连续天数 / 跨零点 / 参数校验） | 12 |
| unit | `tests/unit/test_summary_indexes.py`（迁移 `005` 索引护栏） | 2 |
| contract | `tests/contract/test_summary_contract.py`（字段集合、无时长字段、无记录日期、`invalid_month` / `invalid_date`、未登录 401） | 6 |
| integration | `tests/integration/test_summary_flow.py`（三级着色、四项明细与多轮累加、重新登录一致、跨账号隔离） | 4 |

### T026 性能抽样（10 次请求，本地 SQLite，造数 30 天）

- `GET /api/summary/month`：稳态 p95 ≈ **19ms**（首次冷启动 77ms，max 77ms）
- `GET /api/summary/day`：p95 ≈ **15ms**（max 15ms）
- 均 < 300ms（plan Performance Goals）；按月一次性聚合，无按天循环查询（N+1）

### T027 场景 A–F（自动化等价覆盖，禁用 mock）

| 场景 | 载体 | 结果 |
|---|---|---|
| A 三级着色与分档 | `test_summary_service.py::test_levels_gray_light_deep` / `test_shade_buckets` + 集成 `test_month_colors_today_and_history_days` | PASS |
| B 单日四项明细 | 集成 `test_day_summary_matches_actual_behavior`（含多轮累加） | PASS |
| C 灰色日与未来日期 | 契约 `test_day_without_record_returns_200_with_false` | PASS |
| D 月度汇总与连续天数 | `test_month_total_matches_sum_of_days` + streak 三例（当天未学不归零 / 中断重算 / 无活动为 0） | PASS |
| E 跨月与参数校验 | 契约 `test_month_summary_*` / `test_day_summary_rejects_invalid_date` | PASS |
| F 历史回溯与跨设备一致 | 集成 `test_history_identical_after_relogin`（新 token 后月历与明细完全相等） | PASS |

### T029 冒烟

- `pytest -q` → **全绿（退出码 0）**：共 **187** 个用例（既有 163 + 002 新增 24）
- `npm run build` → `✓ built in 18.24s`（vue-tsc 类型检查通过）

### 审计结论（FR-018 / SC-007）

- 两个端点均不接受 `user_id`，只取当前登录用户（`Depends(get_current_user)`）；未登录 401
- 无新增出站请求、无第三方共享、无导出 / 分享能力；响应不含任何在线时长字段（契约用例断言）
- 跨账号隔离：集成 `test_accounts_cannot_see_each_other`（A 看不到 B 的日历与月度总计）PASS

### T025 三档视口（浏览器实测：Playwright 驱动系统 Edge）

| 视口 | `scrollWidth / clientWidth` | 结论 |
|---|---|---|
| 360 × 780 | 360 / 360 | 无横向滚动、无溢出 |
| 768 × 1024 | 768 / 768 | 同上（导航切换为桌面侧栏） |
| 1440 × 900 | 1440 / 1440 | 同上 |

截图证据（`specs/002-study-calendar-summary/evidence/`）：`summary-360.png`、`summary-768.png`、`summary-1440.png`、`summary-detail-1440.png`、`summary-2026-10.png`。360 下底部导航 6 项（首页 / 学习 / 测验 / 错题 / 总结 / 设置）不挤压；月历 7 列、日期与学习词数均可读。

### T027 手工走查（真实浏览器 + 造数 30 天）

造数：`python scripts/seed_summary_history.py --user stu01 --days 30` → 新增 20 天历史（深绿 / 浅绿混合，另有 10 天无记录）。

| 场景 | 实测结果 |
|---|---|
| A 三级着色与分档 | 深绿日显示学习词数（3 / 6 / 9 / 12 / 15 / 18 / 21 / 24 / 27 / 30，深浅随词数变化），浅绿日仅浅绿底无数字，灰色日最浅；今天（9/30）有独立描边 |
| B 单日明细四项 | 点 9/15：学习单词数 **35**；今日测验「已完成 · 对 8 / 错 2 · 正确率 80%」；错题本专项「1 轮 · 答 4 题（对 3 / 错 1）」；错题库专项同 —— 与造数写入逐项一致 |
| C 灰色日 / 浅绿日 | 点 9/4（灰色）→「当天没有学习记录」；点 9/2（浅绿）→ 学习单词数 0、今日测验未进行、正确率 —（不空白、不报错） |
| D 月度汇总与连续天数 | 9 月：学习词数 **199**（= 各深绿日之和 25+25+12+18+35+25+3+3+35+18）、有活动天数 20、连续学习 1 天；切到 8 月（无活动）→ 0 / 0 / 连续 0 天 |
| E 跨月切换 | 下一月 → 2026-10 全灰、连续 0 天；上一月 → 2026-09 数字与切换前完全一致；再上一月 → 2026-08 全灰 |
| F 重新登录 / 跨设备一致 | 换新 token（重新登录）重载页面 → 连续 1 天 / 199 / 20 / 86 题（对 66 错 20）/ 两类专项各 10 轮 40 题，与切换前逐项一致 |

> 走查环境：真实浏览器访问 `http://127.0.0.1:5173/summary`（Vite dev + `/api` 代理到 `http://127.0.0.1:8000`），全程未使用 mock。
