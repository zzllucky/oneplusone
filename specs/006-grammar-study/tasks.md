# Tasks: 初中英语语法学习（大纲 · 学卡 · 练习）

**Input**: Design documents from `/specs/006-grammar-study/`
**Prerequisites**: [plan.md](./plan.md)（技术栈与结构）、[spec.md](./spec.md)（用户故事与优先级）、[research.md](./research.md)（决策）、[data-model.md](./data-model.md)（实体）、[contracts/api.md](./contracts/api.md)（接口）

**Tests**: 章程 III「测试先行（不可协商）」强制 TDD —— 每个故事先写失败测试，确认失败后再实现。所有测试任务均为必做项。

**Organization**: 按用户故事分组，每个故事可独立实现、独立测试、独立交付。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 所属用户故事（US1 大纲 / US2 学卡 / US3 练习 / US4 错题回链）
- 路径：后端 `backend/src/app/...`、后端测试 `backend/tests/...`、前端 `frontend/src/...`、前端测试 `frontend/tests/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 确认环境就绪与语法模块文件骨架

- [X] T001 确认语法内容层已就绪：`backend` 执行 `alembic upgrade head` 后校验迁移链 001→006 已应用、`grammar_points` 82 行 / `grammar_questions` 约 747 行 / `grammar_options` 约 2988 行，并确认既有全量测试通过（`uv run --extra dev pytest -q`）作为回归基线
- [X] T002 [P] 建立后端语法模块骨架文件：新建 `backend/src/app/models/grammar_progress.py`、`backend/src/app/schemas/grammar.py`、`backend/src/app/services/grammar_service.py`、`backend/src/app/api/grammar.py`（各含中文模块 docstring 与 `from __future__ import annotations`，暂无实现）
- [X] T003 [P] 建立前端语法模块骨架文件：新建 `frontend/src/api/grammar.ts`、`frontend/src/stores/grammar.ts`、`frontend/src/pages/GrammarOutlinePage.vue`、`frontend/src/pages/GrammarCardPage.vue`、`frontend/src/pages/GrammarPracticePage.vue`、`frontend/src/components/GrammarPointItem.vue`、`frontend/src/components/GrammarQuestionCard.vue`（最小可编译占位）

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 数据层、错误码、路由与接口类型 —— 必须全部完成，任何用户故事才能开始

**⚠️ CRITICAL**: 本阶段未完成前不得进入任何用户故事

- [X] T004 新建迁移 `backend/alembic/versions/007_grammar_progress.py`（revision 链 006 → 007，沿用既有"存在则跳过"幂等写法），创建 4 张表并带全部约束：`grammar_point_progress`（`status VARCHAR(12) CHECK(status IN ('not_started','learning','mastered')) DEFAULT 'not_started'`、`UNIQUE(user_id, point_id)`、`INDEX(user_id, status)`）、`grammar_attempts`（`source VARCHAR(8) CHECK(source IN ('card','bank'))`、`level VARCHAR(2) NULL CHECK(level IS NULL OR level IN ('L1','L2','L3'))`、`INDEX(user_id, point_id)`）、`grammar_answers`（`UNIQUE(attempt_id, question_id)`、`INDEX(question_id)`）、`grammar_wrong_points`（`UNIQUE(user_id, point_id)`、`INDEX(user_id, added_at)`）；四表 `user_id`/`point_id` 均 `FK → users.id` / `FK → grammar_points.id` `ON DELETE CASCADE`
- [X] T005 [P] 在 `backend/src/app/models/grammar_progress.py` 定义四个 ORM 模型 `GrammarPointProgress` / `GrammarAttempt` / `GrammarAnswer` / `GrammarWrongPoint`，字段与约束逐条对齐 [data-model.md](./data-model.md)（含 `String(16)` 的 `point_id`、`String(32)` 的 `question_id`、`String(2)` 的 `choice_key`、全部 `NOT NULL` / `DEFAULT` 取值）
- [X] T006 [P] 在 `backend/src/app/models/__init__.py` 导出四个新模型并加入 `__all__`
- [X] T007 [P] 在 `backend/src/app/errors.py` 的 `ERROR_MESSAGES` 登记 6 个错误码：`grammar_point_not_found` / `grammar_question_not_found` / `grammar_attempt_not_found` / `grammar_attempt_already_finished` / `no_grammar_questions` / `invalid_choice_key`（缺登记则 message 退回 code 原文）
- [X] T008 [P] 在 `backend/src/app/schemas/grammar.py` 定义 Pydantic v2 模型（命名沿用 `XxxRequest` / `XxxResponse` / `XxxItem`；**不使用** `ConfigDict(from_attributes=True)`，schema 不接收 ORM 对象）：`GrammarPointItem`、`GrammarOutlineModule`、`GrammarOutlineResponse`、`GrammarPointDetailResponse`、`GrammarViewResponse`、`GrammarQuestionItem`、`GrammarOptionItem`、`AttemptStartResponse`、`GrammarAnswerRequest`、`GrammarAnswerResponse`、`GrammarFinishResponse`、`GrammarWrongPointItem`、`GrammarWrongPointListResponse`
- [X] T009 在 `backend/src/app/main.py` 注册语法路由：`from app.api import grammar` 并 `app.include_router(grammar.router, prefix="/api")`（router 自身 `prefix="/grammar", tags=["grammar"]`）
- [X] T010 [P] 在 `frontend/src/api/grammar.ts` 定义 9 个接口的类型与封装（复用 `./client` 的 `get`/`post`，路径 `/api/grammar/...`，含 `guessPoint(pointId, choiceKey)` 与 `GuessFeedback`），类型字段与 [contracts/api.md](./contracts/api.md) 逐字一致（含 `status: 'not_started' | 'learning' | 'mastered'`、`has_wrong: boolean`、`question_id: string`、`choice_key: string`）

**Checkpoint**: 迁移可升级、路由可注册、前端类型可编译 —— 用户故事实现可开始

---

## Phase 3: User Story 1 - 浏览语法大纲并看到进度 (Priority: P1) 🎯 MVP

**Goal**: 学生进入语法板块即可看到按模块分组的全部知识点、深度标签、掌握状态与顶部汇总计数

**Independent Test**: 登录 → 进入 `/grammar` → 21 个模块分组与 82 个知识点可见 → 全新账号全部为"未学"、顶部"已掌握 0 / 全部 82" → 点击条目跳转学卡页

### Tests for User Story 1 ⚠️ 先写、确认失败

> **NOTE: 这些测试必须先写并确认 FAIL，再开始实现**

- [X] T011 [P] [US1] 单元：`backend/tests/unit/test_grammar_service.py`（`pytestmark = pytest.mark.unit`）断言 `list_outline` 按 `module + order_index` 分组、`mastered_count`/`wrong_count` 聚合正确、无进度时 `status='not_started'`、`question_count` 只统计 `source='bank'`
- [X] T012 [P] [US1] 契约：`backend/tests/contract/test_grammar_contract.py`（`pytestmark = pytest.mark.contract`）断言 `GET /api/grammar/outline` 字段形状、`total_points=82`，并断言语法模块全部 9 个端点在未登录时一律 401 `unauthorized`（FR-018）
- [X] T013 [P] [US1] 前端：`frontend/tests/unit/grammarOutline.spec.ts` 断言按模块分组渲染、状态徽章（`未学 / 学习中 / 已掌握 / 有错题`）与顶部计数

### Implementation for User Story 1

- [X] T014 [US1] 在 `backend/src/app/services/grammar_service.py` 实现 `list_outline(db, user_id) -> dict`：一次查询 `grammar_points` 全表，左连接当前用户 `grammar_point_progress` 与 `grammar_wrong_points`，`JOIN` 统计每个知识点 `source='bank'` 的题数，返回 `{total_points, mastered_count, wrong_count, modules[]}`
- [X] T015 [US1] 在 `backend/src/app/api/grammar.py` 实现 `GET /api/grammar/outline`，`response_model=GrammarOutlineResponse`，依赖 `user: User = Depends(get_current_user), db: Session = Depends(get_db)`
- [X] T016 [US1] 在 `frontend/src/stores/grammar.ts` 实现 `loadOutline()`（Pinia setup store，持有 `outline` / `wrongPoints` / `loading` / `error`，调用 `getOutline()`）
- [X] T017 [US1] 在 `frontend/src/components/GrammarPointItem.vue` 渲染知识点条目：标题、深度标签（核心 / 了解）、状态徽章、`question_count=0` 时练习入口禁用
- [X] T018 [US1] 在 `frontend/src/pages/GrammarOutlinePage.vue` 组装大纲页（模块分组 + 顶部"已掌握 / 全部 / 错题"计数 + 点击跳 `/grammar/{point_id}`），并在 `frontend/src/router/index.ts` 登记 `/grammar` 路由、`frontend/src/components/AppShell.vue` 的 `navItems` 加入 `{ path: '/grammar', label: '语法', icon: '📐' }`

**Checkpoint**: US1 独立可用 —— 大纲可浏览、状态与计数正确

---

## Phase 4: User Story 2 - 看学卡完成一次学习（猜一猜 → 讲解 → 学后检测） (Priority: P1)

**Goal**: 学生打开知识点学卡，走完"猜一猜 → 讲解 → 学后检测"三段式，检测全对即标记掌握

**Independent Test**: 进入任一未学知识点 → 猜一猜选完看反馈 → 阅读讲解 → 做完卡内检测 → 看到本轮结果 → 全对后状态变"已掌握"，大纲计数同步

### Tests for User Story 2 ⚠️ 先写、确认失败

- [X] T019 [P] [US2] 单元：`backend/tests/unit/test_grammar_service.py` 追加 —— `mark_viewed` 幂等置 `learning`（已是 `mastered` 不降级）；`source='card'` 轮次全对结算后 `status='mastered'` 且写入 `mastered_at`；未全对保持 `learning`
- [X] T020 [P] [US2] 契约：`GET /api/grammar/points/{point_id}` 与 `POST /api/grammar/points/{point_id}/check/start` 的响应中**断言不含** `is_correct`、`correct_key`、`explanation`、`feedback`（FR-007 答案保护）；不存在知识点 404 `grammar_point_not_found`
- [X] T021 [P] [US2] 契约：`POST /api/grammar/attempts/{id}/answer` 与 `/finish` —— 全对时 `mastered=true`、`status='mastered'`；非法选项键 422 `invalid_choice_key`；已结束轮次 409 `grammar_attempt_already_finished`；重复提交同一题返回首次结果且不重复计分（FR-015）
- [X] T022 [P] [US2] 集成：`backend/tests/integration/test_grammar_flow.py`（`pytestmark = pytest.mark.integration`）走通"打开学卡 → 标记已学 → 开始检测 → 逐题作答 → 结算 → 大纲计数 +1"
- [X] T023 [P] [US2] 前端：`frontend/tests/unit/grammarQuestionCard.spec.ts` 断言题干与选项渲染、作答后展示对错 + 正确项 + 解析、答错时展示所选错项 feedback
- [X] T051 [P] [US2] 契约：`POST /api/grammar/points/{point_id}/guess` —— 合法键返回所选 `feedback`；非法键 422 `invalid_choice_key`；未登录 401；并断言 `GET /points/{id}` 的 `payload.guess` 无 `answer` 键、`guess.options[*]` 仅含 `key`/`text`（F1 修复，FR-007）
- [X] T052 [P] [US2] 前端：`frontend/tests/unit/grammarCard.spec.ts` 断言"猜一猜"渲染选项（不渲染答案）、点击后调用 `guessPoint()` 并展示返回的 feedback、接口失败时展示错误态可重试

### Implementation for User Story 2

- [X] T024 [US2] 在 `backend/src/app/services/grammar_service.py` 实现 `get_point_card(db, user_id, point_id)`（返回 point + **清洗后的** payload + `source='card'` 题目与选项，**仅 key/text**）、`mark_viewed(db, user_id, point_id)`（幂等）、`start_attempt(db, user_id, point_id, source='card', level=None)`（无题时 `raise AppError("no_grammar_questions", status_code=409)`）；payload 必须经 `sanitize_payload()` 清洗，规则见 [contracts/api.md](./contracts/api.md)「sanitize_payload() 清洗规则」：递归删除 `answer` / `is_correct` / `correct_key` 键，并删除 `guess.options[].feedback`（**不得**原样下发，否则泄露正解）
- [X] T025 [US2] 在同一 service 实现判分核心 `record_answer(db, user_id, attempt_id, question_id, choice_key) -> dict`：校验题目属于该轮次知识点与选项键合法（否则 `AppError("invalid_choice_key", status_code=422)`），`UNIQUE(attempt_id, question_id)` 命中则返回首次结果；一次事务内写 `grammar_answers` → 更新 `grammar_attempts` 计数 → 按 `error_tag` 维护 `grammar_wrong_points`（答错：不存在则插入 `wrong_count=1, correct_streak=0`，存在则 `wrong_count+=1`、`correct_streak=0`、`last_wrong_at=now`、`added_at` 不变；答对：`correct_streak+=1`，`>= GRAMMAR_WRONG_REMOVE_STREAK(2)` 删除该行）→ 返回 `is_correct / correct_key / explanation / feedback / attempt 计数 / added_to_wrong_points / removed_from_wrong_points / correct_streak`
- [X] T026 [US2] 实现 `finish_attempt(db, user_id, attempt_id) -> dict`：回填 `total_count / correct_count / wrong_count / finished_at`，`accuracy = round(correct/total, 4)`（`total=0` 时为 0），`duration_seconds`；`source='card'` 且全对时把 `grammar_point_progress.status` 置 `mastered` 并写 `mastered_at`；已结束（(`finished_at` 非空））时 `raise AppError("grammar_attempt_already_finished", status_code=409)`
- [X] T027 [US2] 在 `backend/src/app/api/grammar.py` 实现 `GET /points/{point_id}`、`POST /points/{point_id}/view`、`POST /points/{point_id}/check/start`、`POST /attempts/{attempt_id}/answer`、`POST /attempts/{attempt_id}/finish`（答案与结算接口同时服务 US3）
- [X] T028 [US2] 在 `frontend/src/components/GrammarQuestionCard.vue` 实现题干 + 选项 + 判分反馈（正确项 / 解析 / 错因），并在 `frontend/src/pages/GrammarCardPage.vue` 实现三段式学卡：猜一猜（点击选项后调 `guessPoint()` 取服务端返回的 `feedback`，**不得**从 payload 本地读取反馈）→ 讲解（按 `card_type` 渲染 `rule` / `contrast` / `memorize` 分支）→ 学后检测（调用 answer/finish）+ 结果；`frontend/src/router/index.ts` 登记 `/grammar/:pointId`
- [X] T053 [US2] 在 `backend/src/app/services/grammar_service.py` 实现 `get_guess_feedback(db, point_id, choice_key) -> str`：从**未清洗**的原始 `payload` 中取 `guess.options` 里匹配 `choice_key` 的 `feedback`（不写库、不判分、不影响掌握状态），键不匹配时 `raise AppError("invalid_choice_key", status_code=422)`；并在 `backend/src/app/api/grammar.py` 实现 `POST /points/{point_id}/guess`，`response_model=GrammarGuessResponse`（F1 修复）

**Checkpoint**: US1 + US2 均独立可用 —— 可学完一个知识点并看到掌握状态

---

## Phase 5: User Story 3 - 做题库练习并即时判分 (Priority: P2)

**Goal**: 学生针对知识点发起题库练习，按 L1 → L2 → L3 递进顺序出题、即时判分、结算给出正确率与用时

**Independent Test**: 进入有题库的知识点 → 发起练习 → 逐题作答看判分与解析 → 结算看正确率 → 中途退出后可重新开始一轮；无题库题的知识点给出明确提示

### Tests for User Story 3 ⚠️ 先写、确认失败

- [X] T029 [P] [US3] 单元：取题严格按 `level`（L1 → L2 → L3）+ `order_index` 递增（不洗牌，R-005）；`level` 过滤只取该层级；无题库题时 `AppError("no_grammar_questions", 409)`；`source='bank'` 结算不改变 `grammar_point_progress.status`
- [X] T030 [P] [US3] 契约：`POST /api/grammar/points/{point_id}/practice/start` —— 正常返回题目顺序正确；无题库题 409 `no_grammar_questions`；`level` 非法 422 `validation_error`；未登录 401
- [X] T031 [P] [US3] 集成：`backend/tests/integration/test_grammar_flow.py` 追加练习链路 —— 开始练习 → 答完全部题目 → 结算（正确率 / 用时）→ 再次发起可重新开始
- [X] T032 [P] [US3] 前端：`frontend/tests/unit/grammarPractice.spec.ts` 断言层级标签展示、逐题推进、结算面板（总题数 / 答对 / 答错 / 正确率）、无题库题时的提示态

### Implementation for User Story 3

- [X] T033 [US3] 在 `backend/src/app/services/grammar_service.py` 复用 `start_attempt` 实现 `source='bank'` 取题：`filter(point_id, source='bank')`，`level` 非空时追加过滤，`order_by(level 顺序 L1<L2<L3, order_index)`；写入 `grammar_attempts(source='bank', level=...)`
- [X] T034 [US3] 在 `backend/src/app/api/grammar.py` 实现 `POST /points/{point_id}/practice/start`，请求体 `{ level?: 'L1'|'L2'|'L3'|null }`，`level` 用 `Query/Body` 校验取值（非法 → `AppError("validation_error", status_code=422)`）
- [X] T035 [US3] 在 `frontend/src/pages/GrammarPracticePage.vue` 实现练习页：发起练习 → 复用 `GrammarQuestionCard.vue` 逐题作答 → 结算面板；`question_count=0` 的知识点不展示练习入口（沿用 T017）
- [X] T036 [US3] 在 `frontend/src/router/index.ts` 登记 `/grammar/:pointId/practice` 路由，并在学卡页提供练习入口

**Checkpoint**: US1–US3 均独立可用 —— 学与练闭环成立

---

## Phase 6: User Story 4 - 语法错题本与回链重学 (Priority: P2)

**Goal**: 答错的知识点自动进入语法错题本，可直达学卡重学，连续答对 2 次自动移出

**Independent Test**: 练习中答错 → 错题本出现该知识点 → 点击直达学卡 → 再练连续答对 2 题 → 自动移出错题本；学后检测答错同样入本

### Tests for User Story 4 ⚠️ 先写、确认失败

- [X] T037 [P] [US4] 单元：错题规则 —— 首次答错插入（`wrong_count=1`、`correct_streak=0`、`added_at` 设定）；再次答错 `wrong_count+=1`、`correct_streak=0`、`last_wrong_at` 更新、`added_at` **不变**；连续答对 2 次删除该行；中途答错则 `correct_streak` 归零
- [X] T038 [P] [US4] 契约：`GET /api/grammar/wrong-points` 字段形状（`point_id / title / module / module_name / wrong_count / correct_streak / added_at / last_wrong_at`）、排序按 `added_at asc, id asc`、未登录 401、空列表返回 `total=0`
- [X] T039 [P] [US4] 集成：全链路闭环 —— 练习答错（`added_to_wrong_points=true`）→ `GET /wrong-points` 命中 → 学后检测答错同样入本 → 连续答对 2 次后 `removed_from_wrong_points=true` 且列表移除
- [X] T054 [P] [US4] 集成：账号隔离（FR-019）—— 用户 A 的进度 / 轮次 / 错题本对用户 B 完全不可见（`GET /outline` 计数为 0、`GET /wrong-points` 为空、B 操作 A 的 `attempt_id` → 404 `grammar_attempt_not_found`）；未完成轮次 —— 中途退出后再次发起创建的是新轮次，旧轮次保持 `finished_at IS NULL` 且不自动结算

### Implementation for User Story 4

- [X] T040 [US4] 在 `backend/src/app/services/grammar_service.py` 实现 `list_wrong_points(db, user_id) -> (rows, total)`：`JOIN grammar_points` 补 `title / module / module_name`，排序 `added_at asc, id asc`
- [X] T041 [US4] 在 `backend/src/app/api/grammar.py` 实现 `GET /api/grammar/wrong-points`，`response_model=GrammarWrongPointListResponse`
- [X] T042 [US4] 在 `frontend/src/pages/GrammarOutlinePage.vue` 增加"只看错题"筛选视图（复用 `GrammarPointItem.vue` 与错题计数），条目点击跳 `/grammar/{point_id}` 直达学卡（FR-014）
- [X] T043 [US4] 在 `frontend/src/stores/grammar.ts` 增加 `loadWrongPoints()` 与 `wrongCount`，大纲页与筛选视图共享

**Checkpoint**: US1–US4 全部独立可用 —— 语法学习闭环完成

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 横切关注点与端到端验收

- [X] T055 [P] 前端三个语法页面的加载态 / 错误态 / 空状态：加载中骨架或 spinner、请求失败展示错误文案 + 重试按钮（文案按后端 `error.code` 映射：`grammar_point_not_found` → 知识点不存在、`no_grammar_questions` → 该知识点暂无练习题、`grammar_attempt_already_finished` → 本轮已结束）、空状态（错题本为空显示引导、无题库题不展示练习入口）
- [X] T044 [P] 在 `backend/src/app/services/grammar_service.py` 补充结构化日志：练习 / 检测发起、判分结果、错题本增删，含 `user_id` 与 `point_id`，**不含**任何身份类信息（FR-022）
- [X] T045 [P] 响应式校验：按 `quickstart.md` 场景 G，在 360 / 768 / 1440 视口核对三个语法页面无横向滚动、导航「语法」入口在窄屏底部导航可见可点
- [X] T046 [P] 隔离回归：按 `quickstart.md` 场景 H，确认语法链路全通后单词模块的每日目标、今日集合、测验解锁与单词错题本与基线一致，`uv run --extra dev pytest -q` 全量通过（FR-020）
- [X] T047 全量校验：`uv run --extra dev pytest -q` + `cd frontend && npm run test` + `npm run typecheck`
- [X] T048 按 [quickstart.md](./quickstart.md) 场景 A–H 逐条端到端走查并记录结果
- [X] T049 [P] 同步文档：`README.md` 功能描述与 `docs/operations.md`（如需）补充语法模块说明与命令
- [X] T050 需求质量自查：按 [checklists/requirements-quality.md](./checklists/requirements-quality.md) 逐条核对 spec 并勾选已满足项，未满足项回改 [spec.md](./spec.md)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，可立即开始
- **Foundational (Phase 2)**: 依赖 Phase 1 完成 —— **阻塞所有用户故事**
- **US1 (Phase 3)**: 依赖 Phase 2；无其他故事依赖
- **US2 (Phase 4)**: 依赖 Phase 2；判分核心（T025）与 answer/finish 端点（T027）同时被 US3 复用
- **US3 (Phase 5)**: 依赖 Phase 2 + T025/T027（判分与结算）
- **US4 (Phase 6)**: 依赖 T025 的错题回链逻辑；列表与前端依赖 Phase 2
- **Polish (Phase 7)**: 依赖 US1–US4 完成

### User Story Dependencies

- **US1 (P1)**：Phase 2 后即可开始，不依赖其他故事（大纲在未学状态下即可完整验收）
- **US2 (P1)**：Phase 2 后即可开始；判分与结算服务被 US3 复用，建议先于 US3
- **US3 (P2)**：依赖 US2 的判分核心（T025）与端点（T027）
- **US4 (P2)**：错题数据由 US2/US3 的判分产生，列表与跳转可独立实现

### Within Each User Story

- 测试 MUST 先写并确认 FAIL，再写实现
- Models → Services → Endpoints → 前端集成
- 每个故事结束停在 Checkpoint 独立验收

### Parallel Opportunities

- Phase 1：T002 与 T003 可并行（后端 / 前端骨架）
- Phase 2：T005、T006、T007、T008、T010 可并行（不同文件）；T004（迁移）先于或独立于模型均可，T009 需 T008 完成
- Phase 3：T011、T012、T013 三个测试可并行；T017 与 T014/T015 可并行（前端组件不依赖后端完成，按契约开发）
- Phase 4：T019–T023 可并行；T028 的前端页面可与 T024–T027 的后端实现并行（按 contracts/api.md 对齐）
- Phase 5/6：同 pattern，测试先行且可并行
- Phase 7：T044、T045、T046、T049 可并行

---

## Parallel Example: User Story 2

```bash
# 测试先行（四路并行，先确认全部 FAIL）：
Task: "T019 [US2] 单元：mark_viewed 幂等 / card 轮次全对置 mastered / 未全对保持 learning"
Task: "T020 [US2] 契约：出题响应不含 is_correct/correct_key/explanation/feedback + 404"
Task: "T021 [US2] 契约：answer/finish 掌握判定 + 422 invalid_choice_key + 409 + 重复提交幂等"
Task: "T023 [US2] 前端：GrammarQuestionCard 作答反馈与解析展示"

# 实现阶段（后端与前端可并行，前端按 contracts/api.md 对齐）：
Task: "T024 [US2] service: get_point_card / mark_viewed / start_attempt"
Task: "T028 [US2] 前端 GrammarCardPage.vue 三段式 + GrammarQuestionCard.vue"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational（CRITICAL — 阻塞所有故事）
3. 完成 Phase 3: US1 语法大纲
4. **STOP and VALIDATE**: 独立验证大纲可浏览、状态与计数正确
5. 可演示后再继续 US2

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. + US1 大纲 → 独立验收 → 可演示（MVP）
3. + US2 学卡 → 独立验收 → 可演示（能学一个知识点）
4. + US3 练习 → 独立验收 → 可演示（能练一个知识点）
5. + US4 错题回链 → 独立验收 → 完整闭环
6. Phase 7 打磨与端到端验收

### Parallel Team Strategy

多人协作时：
1. 共同完成 Setup + Foundational
2. Foundational 完成后：开发者 A 做 US1+US2（学与掌握），开发者 B 做 US3（练习，依赖 A 的判分核心就位），开发者 C 做 US4（错题列表与前端，按契约先行）
3. 各故事独立集成、独立验收

---

## Notes

- [P] 任务 = 不同文件、无未完成依赖；同文件任务不得并行
- [Story] 标签用于需求可追溯（US1–US4 ↔ spec.md）
- 每个故事必须可独立完成与验收
- 实现前必须确认测试 FAIL
- 每个任务或逻辑分组提交一次
- 任何 Checkpoint 都可停下来独立验证
- 全部字段与错误码以 [contracts/api.md](./contracts/api.md) 为唯一契约来源；字段约束以 [data-model.md](./data-model.md) 为准，不得在实现时自由发挥
- 遵守章程：不新增第三方依赖（R-010），不修改既有 001–006 迁移
- **T051–T055 为 F1 修复补充任务**（`/speckit-analyze` 报出的 HIGH 项：payload 原样下发会泄露正解）：契约改为 `sanitize_payload()` 清洗 + 新增 `POST /points/{id}/guess` 端点，反馈在作答之后下发
