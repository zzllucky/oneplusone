# Tasks: 词库循环学习与轮次统计

**Input**: Design documents from `/specs/003-library-cycle-rounds/`

**Prerequisites**: plan.md（技术栈与结构）、spec.md（4 个 User Story）、research.md（R-001–R-008）、data-model.md（`study_rounds` 表与状态机）、contracts/api.md（2 个端点扩字段）、quickstart.md（场景 A–G；本功能不考虑历史账号）

**Tests**: **包含测试任务** —— 依据章程 III（测试先行不可协商）、IV（集成测试覆盖关键接缝）与 plan.md。每个 Story 阶段**先写失败用例并确认其失败**，再实现。

**Organization**: 按 User Story 分阶段；Setup / Foundational / Polish 阶段无 Story 标签。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 所属 User Story（US1–US4）
- 每条任务均给出**确切文件路径**

## Path Conventions

- 后端：`backend/src/app/{models,schemas,services,api}/…`、`backend/tests/{unit,contract,integration}/…`、`backend/alembic/versions/…`、`backend/scripts/…`
- 前端：`frontend/src/{api,pages}/…`
- 与 plan.md「Project Structure」一致（Web application 结构）

---

## Phase 1: Setup

**Purpose**: 确认改造基线与验证工具（项目骨架与依赖已存在，本次**不新增依赖**）

- [X] T001 确认改造基线：在 `backend/` 下执行 `alembic current`（应为 `003_wrong_word_proficiency`）与 `pytest -q`（全绿），把输出记录到本文件末尾的验证记录；不通过则先修复再继续
- [X] T002 [P] Create `backend/scripts/seed_round_cursor.py`: 开发/测试用造数脚本 —— 把指定账号的 `study_rounds.cursor_word_id` 推进到接近 `MAX(words.id)`（参数：`--user`、 `--remaining`，默认 20），供 quickstart 场景 A/B/D/E 使用；仅本地使用，不进 Docker 镜像

---

## Phase 2: Foundational（阻塞所有 User Story）

**Purpose**: 轮次表、迁移与轮次服务 —— 所有 Story 的共同前置

**⚠️ CRITICAL**: 该阶段未完成前不得开始任何 User Story

### 数据模型与迁移

- [X] T003 Create `backend/src/app/models/study_round.py`: `study_rounds` —— `id` PK autoincrement；`user_id` INTEGER NOT NULL FK→`users.id` ON DELETE CASCADE；`round_no` INTEGER NOT NULL（≥1）；`cursor_word_id` INTEGER NOT NULL（下一个待分配单词 id，按 `Word.id` 升序推进）；`started_on` DATE NOT NULL；`covered_at` DATETIME NULL；`completed_at` DATETIME NULL；约束 `UNIQUE(user_id, round_no)`、部分唯一索引 `UNIQUE(user_id) WHERE completed_at IS NULL`、索引 `(user_id, completed_at)`；类注释写明状态机 `进行中 → 已覆盖 → 已完成` 与不变量（同一账号至多一行 `completed_at IS NULL`；`completed_at` 非空 ⇒ `covered_at` 非空；跨轮时游标重置为词库最小 `Word.id`）
- [X] T004 [P] Register `StudyRound` in `backend/src/app/models/__init__.py`（import 与 `__all__` 同步）
- [X] T005 Create `backend/alembic/versions/004_study_rounds.py`（`revision="004"`, `down_revision="003"`）：**仅**建 `study_rounds` 表及上述索引（`downgrade` 删表）；**不回填历史账号**（不考虑已有账号，不读取 `daily_set_items`、不预建任何轮次行）

### 轮次服务

- [X] T006 [P] Create `backend/tests/unit/test_round_service.py`: **先写失败用例** —— 首轮惰性创建（`round_no=1`、游标 = 词库最小 id）、游标按分配推进、游标越界即"已覆盖"、已覆盖 + 收到测验完成信号即"已完成"、已完成轮数统计、补记（已覆盖且覆盖日早于今天 → 次日补 `completed_at`，不伪造测验成绩）、**补记在读取入口触发**：仅调用 `progress()` / `ensure_open_round()`（不生成当日集合）也完成补记（FR-014 / SC-006）、**长期中断（数月）后回来继续当前轮**：游标与 `learned_count` 保留、不重置轮次（US1 验收 5）、同一账号不出现两个进行中轮次
- [X] T007 Create `backend/src/app/services/round_service.py`: 单一职责 —— `ensure_open_round(db,user_id)`、`allocate_word_ids(db,user_id,goal)`（`SELECT id FROM words WHERE id >= cursor ORDER BY id LIMIT goal`）、`advance_cursor(...)`、`rewind_cursor(...)`（每日目标在"当日未开始"时重算，把撤销的单词还给游标，避免漏词）、`mark_covered(...)`、`mark_completed(...)`、`settle_pending_rounds(db,user_id)`（FR-014 补记）、`progress(db,user_id)`（`learned_count` / `total_count` / `pending_quiz`）；**补记在读取入口统一触发**：`ensure_open_round` 与 `progress` 内部**都先调用** `settle_pending_rounds`，保证首页（只看不分配）与学习页（分配）看到同一轮数（research R-004）；`learned_count` 按**游标**推算（`COUNT(words WHERE id < cursor_word_id)`，不按 `daily_set_items` 计数）；`pending_quiz` = 当前轮 `covered_at` 非空且 `completed_at` 为空；不直接删除任何历史数据；关键迁移写结构化日志
- [X] T008 [P] Create `backend/tests/unit/test_study_service_rounds.py`: **先写失败用例** —— 当前轮耗尽后下一次分配开启新一轮（游标归位）、单日集合**不跨轮**（剩余不足目标时只分配剩余，FR-009）、`library_exhausted` 语义改为"本轮剩余不足每日目标"
- [X] T009 Update `backend/src/app/services/study_service.py`: `get_or_create_today_set` 改为消费 `round_service.allocate_word_ids`（替换现有"排除全部历史已学词"逻辑），分配后调用 `advance_cursor`，本轮取空则先开新轮再分配；`today_summary` 的 `library_exhausted` 按 T008 新语义计算；**不改动** `reset_today_set_if_not_started` 与浏览标记逻辑

**Checkpoint**: 轮次表 + 迁移 + 轮次服务可用，单元测试转绿；此时接口尚未暴露轮次信息

---

## Phase 3: User Story 1 - 学完词库后继续有词可学 (Priority: P1) 🎯 MVP

**Goal**: 词库学完后自动进入新一轮（按词库原顺序），学习页不再空、今日测验不再永久锁死

**Independent Test**: 用 T002 脚本把账号推到"仅剩少量单词" → 学完并做完当日测验 → 次日学习页出现新一轮单词 → 测验可正常解锁完成

### Tests for User Story 1 ⚠️（先写，确认 FAIL）

- [X] T010 [P] [US1] Create `backend/tests/integration/test_round_cycle.py`: 真实 SQLite + HTTP 链路 —— 场景 A（耗尽后次日仍有词可学、首页不再是 `0 / 0`）、场景 B（新一轮从词库首个单词开始、按原顺序推进、一轮内无重复）、场景 E（跨轮过渡日当日集合只有剩余单词，不借新轮凑满）、**长期中断后回来继续当前轮**：中断数日再请求，游标与本轮已学数保留、不重新开始一轮

### Implementation for User Story 1

- [X] T011 [US1] Update `backend/src/app/services/quiz_service.py`: `finish_daily_quiz` 成功提交后调用 `round_service.mark_completed`（仅当当前轮已 `covered`）作为"当日测验完成"信号；**响应体字段不变**，不引入新错误码
- [X] T012 [US1] Update `backend/src/app/api/study.py`: `/study/today` 与浏览接口改用新的轮次取词路径（签名、错误码 `word_not_in_today_set` 不变），并为"开启新一轮 / 补记"补结构化日志
- [X] T013 [US1] Extend `backend/tests/integration/test_round_cycle.py`: 场景 D —— 轮末日浏览完最后一词但**未提交测验**，次日该轮被补记为已完成（`completed_rounds` +1），且不产生任何伪造的测验成绩；学生可立即开始新一轮。**补记入口一致性**：次日**先请求 `GET /home/summary`（不进学习页）**也必须看到 +1，且与随后请求 `/study/today`、刷新、重新登录的结果完全一致（FR-014 / SC-006）

**Checkpoint**: US1 完成 —— 词库学完不再卡死；可单独交付

---

## Phase 4: User Story 2 - 显示已完成词库学习的轮数 (Priority: P1)

**Goal**: 首页显示「已完成 N 轮」+ 大字体建议文案；学习页显示本轮进度（本轮已学 / 总数）

**Independent Test**: 完成一轮（浏览 + 当日测验）后首页显示"已完成 1 轮"、学习页显示"第 2 轮 · 本轮已学 X / 2096"；只浏览未测验时轮数不变

### Tests for User Story 2 ⚠️（先写，确认 FAIL）

- [X] T014 [P] [US2] Create `backend/tests/contract/test_rounds_contract.py`: 契约测试 —— `GET /home/summary` 返回 `completed_rounds`（未完成时 `0`）与 `current_round{round_no,learned_count,total_count,pending_quiz}`；`GET /study/today` 返回 `round{round_no,learned_count,total_count,pending_quiz}`；`pending_quiz` 在"本轮已学完但当日测验未完成"时为 `true`（FR-015）；两个端点的 `completed_rounds` / 轮序号在刷新与重新登录后一致；既有字段名与类型不变

### Implementation for User Story 2

- [X] T015 [P] [US2] Update `backend/src/app/schemas/home.py`: `HomeSummary` 增加 `completed_rounds: int = 0` 与 `current_round: RoundProgress | None = None`（`RoundProgress{round_no:int, learned_count:int, total_count:int, pending_quiz:bool}`）
- [X] T016 [P] [US2] Update `backend/src/app/schemas/study.py`: `TodayStudyResponse` 增加 `round: RoundProgress | None = None`（与 T015 复用同一模型定义，含 `pending_quiz`）
- [X] T017 [US2] Update `backend/src/app/services/home_service.py`: `summary()` 经 **`round_service.progress`**（其内部先执行 `settle_pending_rounds`）填入 `completed_rounds` 与 `current_round`（含 `pending_quiz`）；**不得绕过该入口直接查 `study_rounds` 表** —— 否则首页会读到补记前的旧轮数，与学习页不一致（FR-014 / SC-006）；其余字段与既有行为不变
- [X] T018 [P] [US2] Update `backend/src/app/api/home.py`: 仅同步响应模型，端点签名与错误码不变
- [X] T019 [P] [US2] Update `backend/src/app/api/study.py`: `/study/today` 响应带上 `round`（含 `pending_quiz`）
- [X] T020 [P] [US2] Update `frontend/src/api/home.ts`: `HomeSummary` 类型增加 `completed_rounds` 与 `current_round`
- [X] T021 [P] [US2] Update `frontend/src/api/study.ts` 与 `frontend/src/stores/study.ts`: `TodayStudyResponse` 类型增加 `round`，store 增加只读 `round` 计算属性（`today.value?.round ?? null`）供学习页消费
- [X] T022 [US2] Update `frontend/src/pages/HomePage.vue`: 新增轮次卡片「已完成 N 轮 · 当前第 M 轮」（`completed_rounds` 为 `0` 时显示"当前第 1 轮"，US2 验收 1）；以**加大字体**（Tailwind `text-lg` 及以上，≥ 正文 1.5 倍）展示固定文案"建议初中会考前每天坚持学习，至少完成 10 轮"（FR-013；本版文案不随轮数变化）；`current_round.pending_quiz` 为 `true` 时显示提示"本轮单词已学完，完成今日测验即可计入第 N 轮"（FR-015 / US2 验收 4）；**兜底**：轮次字段缺失 / 为 `null` / 接口异常时**不渲染**该卡片，页面其余部分照常显示，不出现空白块或英文错误堆栈
- [X] T023 [US2] Update `frontend/src/pages/TodayStudyPage.vue`: 进度区显示「第 N 轮 · 本轮已学 X / Y」；`round.pending_quiz` 为 `true` 时显示提示"本轮单词已学完，完成今日测验即可计入第 N 轮"（FR-015）；**兜底**：`round` 缺失 / 为 `null` / 接口异常时只显示原有进度，不出现空白块或英文错误堆栈

**Checkpoint**: US1 + US2 均可用 —— 循环学习与轮次展示完整闭环；可作为 MVP 交付

---

## Phase 5: User Story 3 - 新一轮沿用既有学习与测验规则 (Priority: P2)

**Goal**: 新一轮内"先浏览后解锁测验""答错进错题本 / 错题库""改目标的生效规则"与首轮完全一致

**Independent Test**: 在新一轮某日未完成浏览时改目标 → 当日集合立即重算；答错 → 同时进入错题本与错题库；未完成浏览 → 测验仍锁定

### Tests for User Story 3 ⚠️（先写，确认 FAIL）

- [X] T024 [P] [US3] Create `backend/tests/integration/test_round_existing_rules.py`: 新一轮中 —— 未浏览任何词时改目标立即重算、已浏览后改目标当日不变、未完成浏览时 `POST /quiz/daily/start` 仍返回 `409 quiz_locked`、测验答错仍进错题本与错题库

### Implementation for User Story 3

- [X] T025 [US3] Audit `backend/src/app/services/study_service.py::reset_today_set_if_not_started` 与 `backend/src/app/services/quiz_service.py::start_daily_quiz`: 确认两者在新一轮下语义不变；如无需改码，则补充指向本 Story 的注释与 T024 回归测试，避免后续改动误伤

**Checkpoint**: 新一轮与首轮规则一致，回归通过

---

## Phase 6: User Story 4 - 轮次推进不丢失历史 (Priority: P2)

**Goal**: 跨轮不清空历史：每日记录、测验结果、错题本、错题库、后续日历总结的历史明细均不变

**Independent Test**: 跨轮前后对比错题本 / 错题库条数与内容、历史日期的学习与测验记录，完全一致

### Tests for User Story 4 ⚠️（先写，确认 FAIL）

- [X] T026 [P] [US4] Extend `backend/tests/integration/test_round_cycle.py`: 场景 F —— 跨轮前后 `wrong_words`、`wrong_word_archive` 的条数与内容一致；历史 `daily_sets` / `daily_set_items` / `quiz_attempts` 行数与内容一致（注：US4 验收 3 涉及「学习日历总结」历史日期着色，该子项**待 002 实现后回归**，本轮不阻塞交付）

### Implementation for User Story 4

- [X] T027 [US4] Audit `backend/src/app/services/round_service.py` + `backend/src/app/services/study_service.py` + `backend/alembic/versions/004_study_rounds.py`: 确认轮次推进路径**不含任何删除历史数据的语句**，在代码注释中固化该约束并由 T026 回归；同时确认 FR-011 —— 轮次与进度数据仅随既有账号鉴权返回，**无新增出站请求 / 第三方共享 / 跨账号可见路径**（如需，在注释中写明结论）

**Checkpoint**: 全部 User Story 可独立工作

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 并发一致性、前端适配与端到端验证（本功能**不考虑历史账号**，故无迁移回填验证项）

- [X] T028 [P] Extend `backend/tests/unit/test_round_service.py`: 同一账号并发 / 多设备重复调用 `ensure_open_round` 时不产生两个进行中轮次（依赖部分唯一索引）
- [X] T029 [P] 前端验证：`npm run build` 通过，并在 360 / 768 / 1440 三档视口下检查首页轮次卡片与学习页本轮进度的排版（无横向滚动、大字体文案不溢出）
- [X] T030 按 `specs/003-library-cycle-rounds/quickstart.md` 跑通场景 A–G，记录实际结果
- [X] T031 [P] Update `CHANGELOG.md`（及必要的 `docs/`）记录：词库循环学习、轮次统计、迁移 `004`（仅建表，不回填历史账号）
- [X] T032 最终冒烟：`cd backend && pytest -q` 全绿（含 001 既有测试与 003 新增测试）＋ 前端构建通过
- [X] T033 [P] 性能抽样（SC-007）：对 `GET /home/summary` 与 `GET /study/today` 各连续请求 10 次，记录 p95 耗时并确认 < 300ms（plan Performance Goals）；确认轮次信息随既有接口一并返回、未新增额外请求或页面
- [X] T034 [P] Create `backend/tests/unit/test_study_rounds_schema.py`: 迁移 `004` 的**索引护栏** —— 断言 `UNIQUE(user_id, round_no)` 与部分唯一索引 `UNIQUE(user_id) WHERE completed_at IS NULL` 真实存在于 `sqlite_master`（实施中发现 `sqlite_where` 传裸字符串会导致索引静默丢失，详见「实施备注」）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**：无依赖，立即开始（T001 是 T005 的前置：确认迁移 head）
- **Foundational (Phase 2)**：依赖 Setup；**阻塞所有 User Story**（T003 → T004 → T005 → T006/T007 → T008 → T009）
- **US1 (Phase 3)**：依赖 Foundational 完成
- **US2 (Phase 4)**：依赖 Foundational；与 US1 可并行开发（不同文件），但契约测试 T014 需要 US1 的完成信号已实现才能端到端跑通
- **US3 / US4 (Phase 5 / 6)**：依赖 Foundational，可并行；US4 的 T026 复用 US1 的集成测试文件
- **Polish (Phase 7)**：依赖上述 Story 完成

### User Story Dependencies

- **US1（P1）**：Foundational 后即可开始，不依赖其他 Story
- **US2（P1）**：Foundational 后即可开始；端到端验证需 US1 的完成信号
- **US3（P2）**：Foundational 后即可开始（回归性质）
- **US4（P2）**：Foundational 后即可开始（回归性质）

### Within Each User Story

- 测试先行：先写用例 → 确认 FAIL → 再实现 → 转 PASS
- 顺序：模型 → 服务 → 接口 → 前端 → 集成
- 每个 Story 结束停在 Checkpoint 独立验收

### Parallel Opportunities

- Phase 1：T002 与 T001 可并行
- Phase 2：T004 与 T003 之后并行；T006 与 T008 可并行编写
- Phase 3–6：US1 后端 与 US2 前端类型/页面（T020–T023）可并行；US3 与 US4 的测试可并行
- Phase 7：T028 / T029 / T031 / T034 可并行（T033 需接口已就绪，T032 为最终冒烟）

---

## Parallel Example: User Story 2

```text
# 契约测试与前端类型可同时开工（不同文件）：
Task: "T014 [P] [US2] Contract test for /home/summary & /study/today in backend/tests/contract/test_rounds_contract.py"
Task: "T020 [P] [US2] Update frontend/src/api/home.ts types"
Task: "T021 [P] [US2] Update frontend/src/api/study.ts types"

# 后端 schema 与 service 串行（同一链路）：
Task: "T015 [P] [US2] Update backend/src/app/schemas/home.py"
Task: "T016 [P] [US2] Update backend/src/app/schemas/study.py"
  → Task: "T017 [US2] Update backend/src/app/services/home_service.py"
```

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. Phase 1 Setup → 2. Phase 2 Foundational（阻塞项，必须完成）→ 3. Phase 3 US1 → **STOP**：词库学完不再卡死，即消除线上最痛的缺陷 → 可先行验证

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. US1 → 循环学习（消除卡死）→ 可交付
3. US2 → 轮次统计与展示 → 用户点名要的功能完成 → 可交付
4. US3 / US4 → 规则一致性与历史保护回归
5. Polish → 并发一致性、前端适配、端到端验证（无迁移回填项）

### Notes

- 本次**不新增第三方依赖**（既有 FastAPI / SQLAlchemy / Alembic / Vue 栈已足够）
- **不考虑历史账号**（用户明确排除）：迁移 `004` 仅建表与索引，不为已有账号回填轮次行；升级前仍建议备份 `data/app.db`
- 轮次与测验的接缝（`finish_daily_quiz` → `mark_completed`）是最易错处，必须集成测试（禁用 mock）
- 验证记录：见本文件末尾「验证记录（实施阶段）」

---

## 验证记录（实施阶段）

### T001 基线（实施前）

- `alembic current` → `003 (head)`
- `pytest -q` → 131 passed（既有全绿）

### T030 场景 A–G 结果（以自动化用例等价覆盖，手工 UI 复核见下）

| 场景 | 载体 | 结果 |
|---|---|---|
| A 词库学完不再卡死 | `tests/integration/test_round_cycle.py::test_scenario_a_library_exhausted_no_longer_blocks` | PASS |
| B 新一轮按原顺序、每词一次 | `test_scenario_b_new_round_follows_library_order` | PASS |
| C 完成一轮计数（先不做测验不加） | `tests/unit/test_round_service.py` 完成判定 + `tests/contract/test_rounds_contract.py::test_pending_quiz_true_when_covered_without_quiz` | PASS |
| D 轮末补记（**先看首页也一致**） | `test_scenario_d_round_settled_next_day_even_from_home` | PASS |
| E 跨轮过渡日不混轮 | `test_scenario_e_transition_day_does_not_mix_rounds` | PASS |
| F 跨轮不清历史 | `test_scenario_f_history_preserved_across_rounds` | PASS |
| G 跨设备 / 重新登录一致 | `test_scenario_d_...`（刷新 + 重新登录）+ `test_round_fields_stable_across_refresh` | PASS |

手工复核项（需启动前后端）：造数脚本 `python scripts/seed_round_cursor.py --user stu01 --remaining 20` 后按 `quickstart.md` 走查；跨"日"在手工环境需调整服务端时区或次日再验。T029 的 360 / 768 / 1440 三档视口排版（轮次卡片与大字体文案不溢出、无横向滚动）需在浏览器中人工复核（本环境无浏览器自动化）。

### T032 冒烟

- `pytest -q` → **全绿**（退出码 0）。按 `def test_` 统计共 **153** 个用例：unit 63 / contract 43 / integration 47；其中 003 新增 **34** 个（unit 20：`test_round_service.py` 13 + `test_study_rounds_schema.py` 2 + `test_study_service_rounds.py` 5；contract 5：`test_rounds_contract.py`；integration 9：`test_round_cycle.py` 5 + `test_round_existing_rules.py` 4）
- `npm run build` → `✓ built in 4.89s`（vue-tsc 类型检查通过）

### T033 性能抽样（10 次请求，本地 SQLite）

- `GET /api/home/summary`：p95 = 10.1ms（max 52.2ms）
- `GET /api/study/today`：p95 = 42.3ms（max 87.8ms）
- 均 < 300ms（plan Performance Goals）；轮次信息随既有接口一并返回，未新增请求

### 实施备注

- 契约文档中端点沿用 001 契约的 `/quiz/daily/*` 命名；实现路由为 `/api/quiz/today/*`（既有命名，未改动）
- 新增 `round_service.rewind_cursor`：每日目标在"未开始"时重算会把撤销的单词还给游标，避免漏词（既有集成测试 `test_goal_change_reallocates_when_today_not_started` 因此保持通过）
- `study_service.learned_word_ids` 保留但不再参与取词（仅供只读统计）
- **US4 验收 3 回归标注（2026-09-30）**：本项的「学习日历总结的历史日期着色」已由 002（`specs/002-study-calendar-summary`）闭环 —— `/api/summary/month` 按月聚合 `daily_sets` / `quiz_attempts` / `quiz_answers`，历史日期着色与明细在重新登录、换设备后完全一致（集成用例 `tests/integration/test_summary_flow.py`）。003 自身无需再改动。
- **修复的迁移缺陷（实施中发现）**：`004` 的 `op.create_index(..., sqlite_where="completed_at IS NULL")` 传裸字符串会导致 `AttributeError: 'str' object has no attribute '_compiler_dispatch'`，表建好但索引静默丢失（首跑失败、再跑被幂等跳过），单账号单进行中轮次的硬约束会失效。已改为 `sa.text(...)`；本地开发库已重建该表并确认两个索引存在（`tests/unit/test_study_rounds_schema.py` 作为回归护栏）。
