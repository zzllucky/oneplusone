# Tasks: 中考英语单词学习测验与错题本

**Input**: Design documents from `/specs/001-word-study-quiz/`
**Prerequisites**: plan.md（技术栈与结构）、spec.md（8 个 User Story）、research.md（R-001–R-013）、data-model.md（8 张表）、contracts/api.md（约 20 个端点）、quickstart.md（场景 A–H）

**Tests**: 本项目**包含测试任务** —— 依据章程 III（测试先行不可协商）、IV（集成测试覆盖关键接缝）与 plan.md R-011。每个 Story 阶段先写失败用例，再实现。

**Organization**: 按 User Story 分阶段，每个 Story 可独立实现、独立验收、独立交付。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 所属 User Story（US1–US8）；Setup / Foundational / Polish 阶段无 Story 标签
- 每条任务均给出**确切文件路径**

## Path Conventions

- 后端：`backend/src/app/…`、`backend/tests/{unit,contract,integration}/…`、`backend/alembic/versions/…`、`backend/seeds/words.txt`
- 前端：`frontend/src/{api,components,pages,stores,composables,router}/…`、`frontend/tests/…`
- 路径与 plan.md「Project Structure」一致（Web application 结构）

---

## Phase 1: Setup

目标：建立可运行的项目骨架与依赖基线（后端 FastAPI + SQLAlchemy + Alembic + SQLite；前端 Vue 3 + Vite + TS）。

- [X] T001 Create `backend/pyproject.toml` with dependencies & directory skeleton: 依赖 `fastapi` / `uvicorn[standard]` / `SQLAlchemy>=2` / `alembic` / `pydantic` / `pydantic-settings` / `passlib[bcrypt]` / `PyJWT` / `httpx`; dev 依赖 `pytest` / `pytest-cov` / `httpx`; 同时创建目录 `backend/src/app/{models,schemas,services,api}`、`backend/tests/{unit,contract,integration}`、`backend/alembic/versions`、`backend/seeds`、`backend/scripts`
- [X] T002 [P] Create `backend/src/app/config.py`: `pydantic-settings` 配置 —— `JWT_SECRET`（环境变量注入，禁止入库/入日志）、`DB_PATH`（默认 `data/app.db`）、`PRONOUNCE_UPSTREAM_URL`、`PRONOUNCE_TIMEOUT_SECONDS=2`、`PRONOUNCE_CACHE_DIR=data/cache/pronounce`、`DAILY_GOAL_DEFAULT=20`、`TIMEZONE=Asia/Shanghai`
- [X] T003 [P] Create `backend/src/app/db.py`: SQLAlchemy `engine`（SQLite，`PRAGMA journal_mode=WAL`、`PRAGMA busy_timeout=5000`、`check_same_thread=False`）、`SessionLocal`、`Base`、`get_session` 生成器（R-005）
- [X] T004 [P] Scaffold frontend in `frontend/`: `package.json`（vue 3 / vue-router 4 / pinia 2 / vite 5 / typescript / tailwindcss 3 / vitest / @vue/test-utils）、`vite.config.ts`（`@` 别名、dev proxy `/api` → `http://localhost:8000`）、`tsconfig.json`、`index.html`、`tailwind.config.js`、`src/main.ts`
- [X] T005 [P] Create `backend/alembic.ini` + `backend/alembic/env.py` + `backend/alembic/script.py.mako`: 迁移环境接入 `Base.metadata` 与 `config.DB_PATH`
- [X] T006 [P] Create `.gitignore` and `.env.example`: 忽略 `data/`、`.env`、`node_modules`、`dist`、`.venv`；`.env.example` 列出 `JWT_SECRET` / `DB_PATH` / `PRONOUNCE_UPSTREAM_URL` 等键名（不含真实值）
- [X] T007 [P] Configure pytest in `backend/pyproject.toml`: `[tool.pytest.ini_options]` —— `testpaths=["tests"]`、`addopts="-q"`、markers `unit/contract/integration`；覆盖报告 `pytest-cov`
- [X] T008 [P] Configure Vitest in `frontend/vitest.config.ts` + `frontend/tests/setup.ts`: jsdom 环境、全局挂载助手

---

## Phase 2: Foundational（阻塞所有 User Story）

目标：数据模型、迁移、词表种子、安全基座、统一错误、认证依赖、前端骨架与路由守卫、测试基座。**必须先完成**。

### 数据模型与迁移

- [X] T009 Create `backend/src/app/models/base.py` + `backend/src/app/models/__init__.py`: `DeclarativeBase` 与统一 `Base`、公共时间戳列约定
- [X] T010 [P] Create `backend/src/app/models/user.py`: `users` —— `id` PK、`login_name` VARCHAR(32) NOT NULL（3–20 位字母/数字/下划线原文）、`login_name_norm` VARCHAR(32) NOT NULL **UNIQUE**（小写归一，去重与登录匹配）、`nickname` VARCHAR(64) NOT NULL（1–24 字符，**允许重复**）、`password_hash` VARCHAR(255) NOT NULL（bcrypt）、`created_at` NOT NULL（UTC）
- [X] T011 [P] Create `backend/src/app/models/user_setting.py`: `user_settings` —— `user_id` PK FK→`users.id` ON DELETE CASCADE、`daily_goal` INTEGER NOT NULL DEFAULT 20 **CHECK(daily_goal BETWEEN 1 AND 200)**、`updated_at` NOT NULL
- [X] T012 [P] Create `backend/src/app/models/word.py`: `words` —— `id` PK、`spelling` VARCHAR(64) NOT NULL **UNIQUE**、`meaning_zh` VARCHAR(255) NOT NULL、`phrase` VARCHAR(255) NULL、`phonetic` VARCHAR(64) NULL、`created_at` NOT NULL
- [X] T013 [P] Create `backend/src/app/models/daily_set.py`: `daily_sets`（`id`、`user_id` FK CASCADE、`study_date` DATE NOT NULL、`created_at`；**UNIQUE(user_id, study_date)**）与 `daily_set_items`（`id`、`daily_set_id` FK CASCADE、`word_id` FK→`words.id`、`order_index` INTEGER NOT NULL、`viewed_at` DATETIME NULL；**UNIQUE(daily_set_id, word_id)**、INDEX(daily_set_id, order_index)）
- [X] T014 [P] Create `backend/src/app/models/quiz.py`: `quiz_attempts`（`id`、`user_id` FK CASCADE、`kind` VARCHAR(16) **CHECK IN ('daily','review')**、`study_date` DATE NULL、`started_at` NOT NULL、`finished_at` NULL、`total_count` / `correct_count` / `wrong_count` INTEGER NOT NULL DEFAULT 0）与 `quiz_answers`（`id`、`attempt_id` FK CASCADE、`word_id` FK、`question_type` VARCHAR(8) **CHECK IN ('en2zh','zh2en')**、`choice_index` INTEGER NOT NULL、`is_correct` BOOLEAN NOT NULL、`answered_at` NOT NULL；**UNIQUE(attempt_id, word_id)**）
- [X] T015 [P] Create `backend/src/app/models/wrong_word.py`: `wrong_words` —— `id`、`user_id` FK CASCADE、`word_id` FK CASCADE、`added_at` DATETIME NOT NULL；**UNIQUE(user_id, word_id)**、INDEX(user_id, added_at)；注释明确「唯一删除路径 = 专项练习答对」
- [X] T016 Create `backend/alembic/versions/001_initial_schema.py`: 创建 T010–T015 全部表、索引与 CHECK 约束；`downgrade` 反向删除
- [X] T017 Create `backend/seeds/words.txt`: 内置中考课标必会单词，统一格式 `单词 词性.释义 | 短语1；短语2`（FR-011 / FR-012）——**已由用户词表替换为 541 条**（spec 目标约 1600 条），继续扩充只需追加条目后重跑 `002` 幂等 upsert
- [X] T018 [P] Create `backend/scripts/validate_word_seed.py`: 校验 `seeds/words.txt` —— 每行可解析为 `单词 + 词性.释义`、`spelling` 全局唯一且非空、条数达到下限（默认 150，可用 `MIN_WORD_COUNT` 覆盖，扩充词表时同步上调）；异常时非零退出码并打印问题行
- [X] T019 Create `backend/alembic/versions/002_seed_words.py`: 读取 `seeds/words.txt` **幂等 upsert**（按 `spelling`）导入 `words`；重复执行不产生重复行、不覆盖用户数据（R-009）

### 安全与基础设施

- [X] T020 Create `backend/src/app/security.py`: `hash_password` / `verify_password`（`passlib[bcrypt]`，cost 12）、`create_access_token` / `decode_access_token`（JWT HS256，有效期 7 天，密钥取自 `config.JWT_SECRET`）（R-002 / R-003）
- [X] T021 [P] Create `backend/src/app/schemas/common.py`: 统一错误响应 `ErrorResponse{ error: { code, message } }`，并声明 13 个错误码常量：`invalid_credentials`、`login_name_taken`、`weak_password`、`invalid_login_name`、`invalid_nickname`、`unauthorized`、`goal_out_of_range`、`word_not_in_today_set`、`quiz_locked`、`no_wrong_words`、`attempt_not_found`、`question_not_found`、`attempt_already_finished`、`pronunciation_unavailable`
- [X] T022 Create `backend/src/app/errors.py` + 在 `backend/src/app/main.py` 注册异常处理器: 业务异常 → `ErrorResponse`（对应 HTTP 401/404/409/422）；校验异常统一结构
- [X] T023 Create `backend/src/app/api/deps.py`: `get_db`（会话依赖）与 `get_current_user`（解析 Bearer JWT，失效/缺失 → 401 `unauthorized`）
- [X] T024 Create `backend/src/app/main.py`: FastAPI 应用装配、挂载路由前缀 `/api`、注册异常处理器、挂载前端构建产物静态目录 `frontend/dist`（存在时）
- [X] T025 [P] Create `frontend/src/api/client.ts`: fetch 封装 —— 自动附加 `Authorization: Bearer <token>`、解析 `ErrorResponse`、401 时清理 token 并跳转登录
- [X] T026 [P] Create `frontend/src/stores/auth.ts`: Pinia store —— `token` / `user`、`login` / `register` / `logout` / `fetchMe`、token 持久化
- [X] T027 Create `frontend/src/router/index.ts`: 8 个页面路由占位（`/register`、`/login`、`/home`、`/settings`、`/study`、`/quiz`、`/wrong-words`、`/review`）+ 登录守卫（未登录 → `/login` 并记录 `redirect` 以便登录后回跳）
- [X] T028 [P] Create `frontend/src/components/AppShell.vue`: 响应式外壳（手机底部导航 / 桌面侧栏）+ 全局错误提示位
- [X] T029 Create `backend/tests/conftest.py`: 测试基座 —— 每个用例独立临时 SQLite 文件、执行 `alembic upgrade head`（含词表 seed）、`TestClient` fixture、`auth_header(token)` 与 `register_and_login()` 助手
- [X] T030 [P] Create `frontend/tests/setup.ts`: Vitest 全局 setup（`@vue/test-utils` 挂载助手、localStorage mock、fetch mock 基线）

**Checkpoint**: `alembic upgrade head` 一次性建表并导入约 1600 词；未登录请求受限接口返回 401 `unauthorized`；前端 8 个路由可跳转且受守卫保护。

---

## Phase 3: User Story 1 — 注册登录与访问保护 (Priority: P1)

**Goal**: 用户用「登录名 + 密码 + 昵称」自由注册并以「登录名 + 密码」登录；未登录访问受限页面被引导至登录页，登录后回到原目标页；口令仅以 bcrypt 哈希保存。

**Independent Test**: 跑 `quickstart.md` 场景 A（A1–A6）；`tests/integration/test_auth_flow.py` 通过。

### Tests ⚠️（先写，必须验证为失败后再实现）

- [X] T031 [P] [US1] Unit tests in `backend/tests/unit/test_security.py`: `hash_password` 输出 ≠ 明文且两次哈希不同；`verify_password` 正确/错误口令；JWT 签发→解码回 `user_id`；过期/篡改 token 被拒
- [X] T032 [P] [US1] Contract tests in `backend/tests/contract/test_auth_contract.py`: `POST /api/auth/register` 201 且响应 `{user:{id,login_name,nickname}}`；`login_name` 非 3–20 位字母/数字/下划线 → 422 `invalid_login_name`；`nickname` 空或 >24 → 422 `invalid_nickname`；`password` < 6 → 422 `weak_password`；重复登录名（含仅大小写不同）→ 409 `login_name_taken`；`POST /api/auth/login` 200 且 `token_type=bearer`；错误口令/不存在登录名 → 401 `invalid_credentials`（两者提示一致）；`GET /api/auth/me` 200 含 `daily_goal`
- [X] T033 [P] [US1] Integration test in `backend/tests/integration/test_auth_flow.py`: 注册 → 登出 → 用同一凭据登录 → 用 `STU01`/`stu01` 两种大小写登录均成功 → 未带 token 访问 `/api/settings` 等受限接口 → 401
- [X] T034 [P] [US1] Frontend unit tests in `frontend/tests/unit/authStore.spec.ts`: register/login 成功后写入 token 与 user；logout 清空；401 响应触发跳转登录

### Implementation

- [X] T035 [US1] Create `backend/src/app/schemas/auth.py`: `RegisterRequest{login_name, nickname, password}`、`LoginRequest{login_name, password}`、`UserOut{id, login_name, nickname}`、`TokenResponse{access_token, token_type, user}`
- [X] T036 [US1] Create `backend/src/app/services/auth_service.py`: `register`（登录名格式校验 + `login_name_norm=lower()` 去重 + 昵称 1–24 + 口令 ≥6 位不限字符组合 + bcrypt 哈希 + **同时创建 `user_settings` 默认 `daily_goal=20`**）、`authenticate`（按 norm 匹配，失败一律 `invalid_credentials`）、`get_user_by_id`
- [X] T037 [US1] Create `backend/src/app/api/auth.py`: `POST /api/auth/register`（201）、`POST /api/auth/login`（200）、`GET /api/auth/me`（200，依赖 `get_current_user`）；注册即登录返回 token
- [X] T038 [US1] Create `frontend/src/api/auth.ts`: `register` / `login` / `fetchMe` 封装（对应 `contracts/api.md` 字段）
- [X] T039 [P] [US1] Create `frontend/src/pages/RegisterPage.vue`: 登录名 / 昵称 / 密码三项输入 + 前端同规则校验提示 + 注册成功后进入首页
- [X] T040 [P] [US1] Create `frontend/src/pages/LoginPage.vue`: 登录名 + 密码；失败显示通用提示（不透露账号是否存在）；登录后跳转 `redirect` 或首页
- [X] T041 [US1] Update `frontend/src/router/index.ts`: 接入 `auth` store 守卫 —— 受限路由未登录跳 `/login?redirect=…`，登录后回跳原目标页
- [ ] T042 [US1] Run `quickstart.md` 场景 A（A1–A6）人工验收并记录结果

**Checkpoint**: 场景 A 全绿；口令哈希不出现在任何响应与日志中。

---

## Phase 4: User Story 2 — 设定每日单词目标 (Priority: P1)

**Goal**: 用户在设置页设定每日单词目标（1–200，默认 20），配置持久化；当日已生成的集合不受影响，新目标次日生效。首页展示昵称、今日进度、每日目标与错题总数。

**Independent Test**: 场景 B（B1–B4）；`tests/integration/test_settings_flow.py` 通过。

### Tests ⚠️

- [X] T043 [P] [US2] Contract tests in `backend/tests/contract/test_settings_contract.py`: `GET /api/settings` 200 含 `daily_goal` / `updated_at`；`PUT` 合法值 200；`0` 或 `300` → 422 `goal_out_of_range`；未登录 → 401
- [X] T044 [P] [US2] Integration test in `backend/tests/integration/test_settings_flow.py`: 改为 30 → 重新登录后仍为 30；当日学习已开始后改目标 → 当日集合数量**不变**（次日生效）；`GET /api/home/summary` 返回 `user` / `daily_goal` / `today` / `wrong_word_count` 四组字段

### Implementation

- [X] T045 [US2] Create `backend/src/app/schemas/settings.py` and `backend/src/app/schemas/home.py`: `SettingsOut{daily_goal, updated_at}`、`SettingsUpdate{daily_goal}`、`HomeSummary{user, daily_goal, today{study_date,total_count,viewed_count,all_viewed,quiz_unlocked}, wrong_word_count}`
- [X] T046 [US2] Create `backend/src/app/services/settings_service.py`: `get_settings`（缺省创建 20）、`update_settings`（校验 1–200，否则 `goal_out_of_range`）
- [X] T047 [US2] Create `backend/src/app/api/settings.py`: `GET` / `PUT /api/settings`（均需认证）
- [X] T048 [US2] Create `backend/src/app/api/home.py` + `services/home_service.py`: `GET /api/home/summary` —— 聚合昵称、今日进度、每日目标、错题总数（进度与错题数在 US3/US5 阶段接入真实数据，本阶段可返回 0 占位）
- [X] T049 [P] [US2] Create `frontend/src/api/settings.ts` and `frontend/src/api/home.ts`: 对应接口封装
- [X] T050 [US2] Create `frontend/src/pages/SettingsPage.vue`: 显示当前目标、输入并保存、越界提示（1–200）、保存成功反馈
- [ ] T051 [US2] Create `frontend/src/pages/HomePage.vue`: 展示用户名昵称、每日目标、今日学习进度卡片（占位）、错题总数量（占位）；随后 Run 场景 B 验收

**Checkpoint**: 场景 B 全绿；目标配置跨会话保持。

---

## Phase 5: User Story 3 — 今日单词学习与发音 (Priority: P1)

**Goal**: 首次进入学习页按每日目标从未学单词分配当日集合（当日稳定）；逐词展示英文/中文释义/常用短语/音标并提供发音播放；标记【已浏览】并累计进度。

**Independent Test**: 场景 C（C1–C5）；`tests/integration/test_study_flow.py` 与 `test_pronounce.py` 通过。

### Tests ⚠️

- [X] T052 [P] [US3] Unit tests in `backend/tests/unit/test_study_allocation.py`: `study_date` 按 **Asia/Shanghai (UTC+8)** 计算；集合数量 = `min(daily_goal, 未学习单词数)`；未学单词按 `words.id` 升序；已出现在任意 `daily_set_items` 的单词不再被分配；`library_exhausted` 判定
- [X] T053 [P] [US3] Contract tests in `backend/tests/contract/test_study_contract.py`: `GET /api/study/today` 200 且 items 含 `word_id/spelling/meaning_zh/phrase/phonetic/order_index/viewed_at`；`POST /api/study/today/items/{word_id}/view` 200 且返回 `viewed_count/all_viewed/quiz_unlocked`；非当日集合的 `word_id` → 404 `word_not_in_today_set`
- [X] T054 [P] [US3] Integration test in `backend/tests/integration/test_study_flow.py`: 首次访问生成 20 词 → 再次访问集合与顺序不变；标记浏览后进度 +1；**重复标记同一词幂等**（`viewed_at` 保持首次）；全部标记后 `all_viewed=true` 且 `quiz_unlocked=true`
- [X] T055 [P] [US3] Integration test in `backend/tests/integration/test_pronounce.py`: 上游返回音频 → 200 `audio/mpeg` 且写入缓存文件；上游 404 / 超时 / 异常 → 404 `pronunciation_unavailable`；第二次请求命中缓存不再访问上游

### Implementation

- [X] T056 [US3] Create `backend/src/app/schemas/study.py`: `StudyWordItem{word_id, spelling, meaning_zh, phrase, phonetic, order_index, viewed_at}`、`TodayStudyResponse{study_date, total_count, viewed_count, all_viewed, quiz_unlocked, library_exhausted, items[]}`、`ViewWordResponse{word_id, viewed_count, total_count, all_viewed, quiz_unlocked}`
- [X] T057 [US3] Create `backend/src/app/services/study_service.py`: `get_or_create_today_set`（`(user_id, study_date)` 唯一，首次生成；从未学单词升序取 `min(goal, 剩余)`）、`mark_viewed`（幂等）、`today_summary`（`viewed_count` / `total_count` / `all_viewed` / `quiz_unlocked`）
- [X] T058 [US3] Create `backend/src/app/api/study.py`: `GET /api/study/today`、`POST /api/study/today/items/{word_id}/view`
- [X] T059 [US3] Create `backend/src/app/services/pronounce_service.py`: `httpx` 请求上游发音地址（`PRONOUNCE_TIMEOUT_SECONDS=2`）、响应非空且 Content-Type 为音频 → 写入 `PRONOUNCE_CACHE_DIR/<word>.mp3` 并返回字节；**无结果 / 超时 / 异常 → 抛 `PronunciationUnavailable`**（R-004）
- [X] T060 [US3] Create `backend/src/app/api/pronounce.py`: `GET /api/pronounce/{word}` —— 命中缓存直接返回，否则走 T059；失败 → 404 `pronunciation_unavailable`
- [X] T061 [US3] Create `frontend/src/api/study.ts`: `fetchTodayStudy` / `markWordViewed` / `pronounceUrl(word)` 封装
- [X] T062 [P] [US3] Create `frontend/src/composables/useSpeech.ts`: 浏览器语音降级 —— `speechSynthesis` 以 `lang=en-US` 朗读；接口不可用时返回 `false` 供 UI 提示（不抛错、不阻断）
- [X] T063 [P] [US3] Create `frontend/src/components/PronounceButton.vue`: 请求 `/api/pronounce/{word}` 播放；收到 404 或播放失败 → 调用 `useSpeech` 降级；两者均不可用 → 明确提示且不影响继续学习
- [X] T064 [US3] Create `frontend/src/components/WordCard.vue`: 展示英文单词、中文释义、常用短语、音标（有则显示）+ 挂载 `PronounceButton` + 【已浏览】按钮
- [X] T065 [US3] Create `frontend/src/stores/study.ts`: 今日集合、当前索引、进度、标记浏览 action、完成态
- [X] T066 [US3] Create `frontend/src/pages/TodayStudyPage.vue`: 逐词展示 + `已浏览数 / 总数` 进度 + 标记后自动切到下一个未浏览词 + 全部完成显示「今日学习已完成」
- [X] T067 [US3] Update `frontend/src/router/index.ts` 与 `HomePage.vue`: 注册 `/study`；首页接入真实今日进度
- [ ] T068 [US3] Run `quickstart.md` 场景 C（C1–C5）人工验收并记录结果

**Checkpoint**: 场景 C 全绿；发音在接口可用与不可用两种情况下都能出声且不报错。

---

## Phase 6: User Story 4 — 今日单词测验（浏览完成后解锁） (Priority: P1)

**Goal**: 仅当日单词全部浏览后可进入测验；题目为英译中/中译英四选一随机（干扰项来自词库且去重，正确答案不下发）；答错加入错题本，**答对不删除任何错题记录**；完成输出结果报告。

**Independent Test**: 场景 D（D1–D3）+ 场景 E（E1–E4）；`test_quiz_lock.py` 与 `test_quiz_flow.py` 通过。

### Tests ⚠️

- [X] T069 [P] [US4] Unit tests in `backend/tests/unit/test_quiz_generation.py`: 题量 = 当日单词数且每词一题；题型 `en2zh`/`zh2en` 随机；选项恒为 4 项、恰好 1 项正确；干扰项取自词库其他单词且与正确答案文本不重复；生成结果**不含**正确项索引
- [X] T070 [P] [US4] Contract tests in `backend/tests/contract/test_quiz_contract.py`: `POST /api/quiz/today/start` 200 且每个 question 含 `question_id/word_id/type/prompt/options[4]`；未全部浏览 → 409 `quiz_locked`；`answer` 200 含 `is_correct/correct_index/added_to_wrong_words`；`finish` 200 含 `total_count/correct_count/wrong_count/accuracy/duration_seconds/new_wrong_words`
- [X] T071 [P] [US4] Integration test in `backend/tests/integration/test_quiz_lock.py`: 只浏览部分单词 → `start` 返回 409 `quiz_locked`（模拟"直接访问地址"同样被拒）；全部浏览后 → 200；`today.quiz_unlocked` 与之一致
- [X] T072 [P] [US4] Integration test in `backend/tests/integration/test_quiz_flow.py`: **关键约束** —— 先制造错题（答错某词），再在今日测验中把该词**答对**，断言 `GET /api/wrong-words` 中该词**仍然存在**（FR-026）；答错 → 错题入本且 `added_at` 记录；重复答错同一词不新增记录、`added_at` 不变；`finish` 报告数值与作答明细一致
- [X] T073 [P] [US4] Frontend unit tests in `frontend/tests/unit/QuizQuestion.spec.ts`: 渲染 4 个选项、点击后展示对错与正确答案、答题后进入下一题

### Implementation

- [X] T074 [US4] Create `backend/src/app/schemas/quiz.py`: `QuizQuestionItem{question_id, word_id, type, prompt, options[]}`、`QuizStartResponse{attempt_id, questions[]}`、`QuizAnswerRequest{question_id, choice_index}`、`QuizAnswerResponse{question_id, is_correct, correct_index, added_to_wrong_words}`、`QuizFinishResponse{attempt_id, total_count, correct_count, wrong_count, accuracy, duration_seconds, new_wrong_words[]}`
- [X] T075 [US4] Create `backend/src/app/services/quiz_service.py` (part 1): `build_questions(word_ids)` —— 题型随机、干扰项从全词库随机取 3 个且文本去重、不下发正确索引；`start_daily_quiz` —— **校验 `viewed_count == total_count`，否则抛 `quiz_locked`**；当日存在未完成 attempt 则复用
- [X] T076 [US4] Update `backend/src/app/services/quiz_service.py` (part 2): `record_daily_quiz_answer` —— 答错 → `wrong_words` 插入（唯一键冲突则忽略，**保留首次 `added_at`**）；**答对 → 不执行任何删除操作**（注释标注 FR-026 硬性约束）
- [X] T077 [US4] Update `backend/src/app/services/quiz_service.py` (part 3): `finish_attempt` —— 计算 `correct_count` / `wrong_count` / `accuracy` / `duration_seconds` / `new_wrong_words[]`，置 `finished_at`
- [X] T078 [US4] Create `backend/src/app/api/quiz.py`: `POST /api/quiz/today/start`、`POST /api/quiz/today/answer`、`POST /api/quiz/today/finish`（均需认证）
- [X] T079 [US4] Create `frontend/src/api/quiz.ts`: `startDailyQuiz` / `answerDaily` / `finishDaily`
- [X] T080 [P] [US4] Create `frontend/src/components/QuizQuestion.vue`: 题干 + 4 选项 + 提交后立即反馈对错与正确答案 + 进入下一题
- [X] T081 [P] [US4] Create `frontend/src/components/QuizResult.vue`: 今日测验结果报告卡（题目数、答对数、正确率、用时、本轮新增错题）
- [X] T082 [US4] Create `frontend/src/pages/TodayQuizPage.vue`: 开始/答题/完成三态；未解锁时展示锁定原因并返回入口
- [X] T083 [US4] Update `frontend/src/pages/TodayStudyPage.vue` and `frontend/src/pages/HomePage.vue`: 测验入口在 `quiz_unlocked=false` 时**置灰不可点击**并提示「请先完成今日全部单词浏览」
- [ ] T084 [US4] Run `quickstart.md` 场景 D（D1–D3）与场景 E（E1–E4）人工验收并记录结果

**Checkpoint**: 场景 D + E 全绿；**未完成浏览 100% 无法开始测验**（含直连地址）。

---

## Phase 7: User Story 5 — 错题本列表 (Priority: P1)

**Goal**: 错题本展示全部错题与加入时间；首页展示错题总数；错题**不因**日期切换、重新登录、学习新单词、今日测验答对而减少。

**Independent Test**: 场景 F（F1–F4）；`test_wrong_word_persistence.py` 通过。

### Tests ⚠️

- [X] T085 [P] [US5] Contract tests in `backend/tests/contract/test_wrong_words_contract.py`: `GET /api/wrong-words` 200 含 `total/page/page_size/items[]`，item 含 `word_id/spelling/meaning_zh/phrase/phonetic/added_at`；空列表返回 `total=0` 且 `items=[]`
- [X] T086 [P] [US5] Integration test in `backend/tests/integration/test_wrong_word_persistence.py`: 依次执行「切换日期 → 重新登录 → 学习新单词 → 今日测验答对该错题词」，每次断言错题数量与内容**完全不变**（FR-031 / SC-004）；同一词重复答错仍只有一条且 `added_at` 为首次时间

### Implementation

- [X] T087 [US5] Create `backend/src/app/schemas/wrong_word.py`: `WrongWordItem{word_id, spelling, meaning_zh, phrase, phonetic, added_at}`、`WrongWordListResponse{total, page, page_size, items[]}`
- [X] T088 [US5] Create `backend/src/app/services/wrong_word_service.py`: `list_wrong_words(db, user_id, page, page_size)`（`added_at` 倒序或升序需与契约一致）、`count_wrong_words`
- [X] T089 [US5] Create `backend/src/app/api/wrong_words.py`: `GET /api/wrong-words`（分页参数 `page` / `page_size`）
- [X] T090 [US5] Create `frontend/src/api/wrongWords.ts`: `fetchWrongWords(page, pageSize)`
- [X] T091 [P] [US5] Create `frontend/src/components/WrongWordItem.vue`: 单词、中文释义、短语、加入错题本时间（格式化展示）
- [X] T092 [US5] Create `frontend/src/stores/wrongWords.ts`: 列表、总数、刷新 action（测验/练习结束后同步）
- [X] T093 [US5] Create `frontend/src/pages/WrongWordsPage.vue` 并注册路由 `/wrong-words`: 列表 + 空状态提示 + 进入专项练习入口；首页接入真实错题总数
- [ ] T094 [US5] Run `quickstart.md` 场景 F（F1–F4）人工验收并记录结果

**Checkpoint**: 场景 F 全绿；四类操作后错题数量变化均为 0。

---

## Phase 8: User Story 6 — 错题专项复习练习（答对方可移除） (Priority: P1)

**Goal**: 题目仅取自错题本；题型与今日测验一致；答错保留（`added_at` 不变），**答对即从错题本删除（唯一移除路径）**；结束输出练习报告。

**Independent Test**: 场景 G（G1–G5）；`test_review_flow.py` 通过。

### Tests ⚠️

- [X] T095 [P] [US6] Contract tests in `backend/tests/contract/test_review_contract.py`: `POST /api/quiz/review/start` 200；错题本为空 → 409 `no_wrong_words`；`answer` 200 含 `is_correct/correct_index/removed_from_wrong_words`；`finish` 200 含 `remaining_wrong_count`
- [X] T096 [P] [US6] Integration test in `backend/tests/integration/test_review_flow.py`: 题目集合 == 当前错题集合（不含非错题）；**答对 → 该词从 `wrong_words` 删除且 `total` 减一（唯一删除路径）**；答错 → 仍在且 `added_at` 不变；完成后 `remaining_wrong_count` 与实际一致

### Implementation

- [X] T097 [US6] Update `backend/src/app/services/quiz_service.py` (review): `start_review_quiz`（题目来源**仅** `wrong_words`，空则 `no_wrong_words`）、`record_review_answer`（答错 → 不写任何错题变更；**答对 → DELETE，这是全项目唯一删除错题的代码路径**，注释标注 FR-031/FR-038）、`finish_review`（报告含 `remaining_wrong_count`）
- [X] T098 [US6] Update `backend/src/app/api/quiz.py`: 新增 `POST /api/quiz/review/start`、`POST /api/quiz/review/answer`、`POST /api/quiz/review/finish`
- [X] T099 [US6] Create `frontend/src/pages/ReviewQuizPage.vue` 并注册路由 `/review`: 复用 `QuizQuestion` 组件，结束后展示专项练习报告（题目数、答对数、答错数、剩余错题数）
- [X] T100 [US6] Update `frontend/src/pages/WrongWordsPage.vue`: 专项练习入口在错题为空时**不可用**并提示「暂无错题」
- [ ] T101 [US6] Run `quickstart.md` 场景 G（G1–G5）人工验收并记录结果

**Checkpoint**: 场景 G 全绿；专项练习答对后错题即时消失。

---

## Phase 9: User Story 7 — 手机 / 平板 / 电脑多设备访问 (Priority: P2)

**Goal**: 8 个页面在 360 / 768 / 1440 三种视口下均无需横向拖动即可完成全流程; 平板横竖屏可用, 触摸不误触; 同一账号跨设备数据一致; 同一网络内的手机 / 平板可通过网络地址访问。

**Independent Test**: 场景 H1 / H1b / H1c / H4 / H5；`responsive.spec.ts` 通过。

### Tests ⚠️

- [X] T102 [P] [US7] Frontend tests in `frontend/tests/unit/responsive.spec.ts`: 关键页面在 360 / 768 / 1440 视口渲染无横向溢出（`scrollWidth <= clientWidth`）；按钮触控区 ≥ 44px

### Implementation

- [X] T103 [US7] Update `frontend/src/components/AppShell.vue`: 手机底部导航、平板/桌面侧栏，断点 `sm/md/lg`
- [X] T104 [US7] Update all 8 pages in `frontend/src/pages/`: 统一栅格与间距，消除窄屏横向滚动与元素挤压
- [ ] T105 [US7] Run `quickstart.md` 场景 H1 三视口走查「学习 → 测验 → 错题本 → 专项练习」并记录结果
- [X] T120 [US7] Update `frontend/index.html` 与 `frontend/src/components/AppShell.vue`: 浏览器标签标题与站内页头统一为产品名称 "1+1=2"（FR-044）
- [ ] T121 [US7] 平板（768–1024px）横竖屏走查并治理布局: 导航可达、无过度拉伸与大片留白、切换后进度不丢失（FR-042）
- [ ] T122 [US7] 触摸可达性审查: 主要按钮可触摸区 ≥ 44×44、关键信息不依赖 hover、发音由点击手势触发（FR-045 / FR-046 / FR-049）
- [ ] T123 [US7] 同账号跨设备一致性验证: 电脑 + 手机/平板同时登录, 每日目标 / 学习进度 / 错题本条数差异为 0, 不互踢（FR-047）
- [ ] T124 [US7] 局域网访问落地: 服务监听所有网卡 + 放行端口说明, 手机 / 平板通过网络地址完成全流程（FR-048）

**Checkpoint**: 三视口全流程无横滑; 手机 / 平板通过局域网地址可登录并使用; 浏览器标签与页头均显示 "1+1=2"。

---

## Phase 10: User Story 8 — 单词发音播放与降级 (Priority: P2)

**Goal**: 有发音结果时播放音频；接口无结果/失败/超时自动降级浏览器语音；两者皆不可用时明确提示且不阻断学习。

**Independent Test**: 场景 C4 + H（含断网）；`test_pronounce_service.py` 与 `useSpeech.spec.ts` 通过。

### Tests ⚠️

- [X] T106 [P] [US8] Unit tests in `backend/tests/unit/test_pronounce_service.py`: 上游 200/404/超时/异常四种分支；缓存命中不发起上游请求；失败时**不写入半文件**
- [X] T107 [P] [US8] Frontend unit tests in `frontend/tests/unit/useSpeech.spec.ts`: 接口不可用 → 调用语音合成；语音合成不可用 → 返回 false 且组件提示不阻断

### Implementation

- [X] T108 [US8] Update `backend/src/app/services/pronounce_service.py`: 缓存目录初始化与按 `word` 命名的文件策略；写入使用临时文件 + 原子替换；失败不落盘
- [X] T109 [US8] Update `frontend/src/composables/useSpeech.ts`: `lang=en-US`、语音不可用检测与提示文案（不抛错）
- [ ] T110 [US8] Run `quickstart.md` 场景 C4 与 H（含断开公网的降级验证）人工验收并记录结果

**Checkpoint**: 发音 100% 出声或明确降级提示，无错误页面。

---

## Phase 11: Polish & Cross-Cutting Concerns

- [X] T111 Create `Dockerfile`: 多阶段 —— Node 构建前端 → 产物拷入 `python:3.12-slim` → `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- [X] T112 [P] Create `docker-compose.yml`: 单服务；卷挂载 `./data:/app/data`（SQLite 文件 + 发音缓存）；注入 `JWT_SECRET`
- [X] T113 [P] Create `backend/src/app/logging.py`: 结构化日志 —— 请求、测验结果、发音代理失败；**MUST NOT 记录明文口令、哈希或 token**
- [X] T114 [P] Create `docs/operations.md`: 备份 `data/app.db`（拷贝即备份）、`alembic upgrade head` 升级步骤、`002` 词表 seed 幂等替换说明、回滚方式
- [X] T115 [P] Create `README.md`: 本地启动（后端 `uvicorn` + 前端 `npm run dev`）、Docker 一键启动、测试命令、词表替换方法
- [X] T116 Run 全量回归: `cd backend && pytest -q` 与 `cd frontend && npm run test`，确认场景 A–H 用例全绿
- [ ] T117 Run `quickstart.md` 场景 A–H 全量人工验收并输出验收记录
- [ ] T118 Performance smoke: 接口 p95 < 300ms、发音 2s 未返回即降级、首屏可交互 < 2s（记录实测值）
- [ ] T119 Verify persistence: 重启服务后重新登录，每日目标、学习进度、错题本与重启前一致（SC-008）
- [X] T120 Create `CHANGELOG.md` and initialize semantic version `0.1.0`（章程 V 版本纪律）

---

## Dependencies

### Story Completion Order

```text
Phase 1 Setup ──> Phase 2 Foundational ──> US1 (Phase 3) ──> US2 (Phase 4)
                                                                  │
                                              ┌───────────────────┴───────────────────┐
                                              ▼                                       ▼
                                        US3 (Phase 5)                            （首页占位）
                                              │ 学习页 + 发音端点
                                              ▼
                                        US4 (Phase 6) 测验（依赖 US3 的浏览与解锁 + US5 的错题写入）
                                              │
                                              ▼
                                        US5 (Phase 7) 错题本列表
                                              │
                                              ▼
                                        US6 (Phase 8) 专项练习（依赖错题数据）
                                              │
                                    ┌─────────┴──────────┐
                                    ▼                    ▼
                             US7 (Phase 9)        US8 (Phase 10)
                                    └─────────┬──────────┘
                                              ▼
                                      Phase 11 Polish
```

### 关键依赖说明

- **US4 与 US5 交叉**：US4 的「答错入本」需要 `wrong_words` 写入能力，US5 只负责读取与展示。实现顺序建议 **US4 的 `record_daily_quiz_answer` 先落地**（T076），US5 直接消费；US4 的验收断言（答对不删错题）需要 US5 的 `GET /api/wrong-words`，可用 `T089` 之后补齐，或在集成测试中直接查库断言。
- **US6 强依赖 US5**：题目来源与移除目标都是错题本。
- **US8 依赖 US3**：`/api/pronounce/{word}` 与 `PronounceButton` 骨架在 US3 建立，US8 只做缓存策略与降级强化。
- **US7 依赖全部页面存在**：建议在 US1–US6 页面齐备后再做响应式统一治理。
- **T017（词表种子）阻塞所有学习/测验类任务**：任何读取 `words` 表的代码 MUST 在 `alembic upgrade head` 之后运行。

### Phase 内并行机会

- **Phase 1**: T002 / T003 / T004 / T005 / T006 / T007 / T008 可并行（不同文件）
- **Phase 2**: T010–T015 六个模型文件可并行；T018 与 T020 可并行；T025 / T026 / T028 / T030 可并行；**T016（迁移 001）必须在全部模型文件完成后执行**；**T019（seed 迁移）依赖 T017 词表文件**
- **Phase 3**: T031 / T032 / T033 / T034 可并行；T039 / T040 可并行
- **Phase 4**: T043 / T044 可并行；T049 与 T050 可并行
- **Phase 5**: T052–T055 四个测试可并行；T062 / T063 可并行
- **Phase 6**: T069–T073 可并行；T080 / T081 可并行；**T075→T076→T077 为同文件顺序任务，不得并行**
- **Phase 7**: T085 / T086 可并行
- **Phase 8**: T095 / T096 可并行；**T097 与 T076 同处 `quiz_service.py`，须在 T076 之后顺序进行**
- **Phase 10**: T106 / T107 可并行

---

## Parallel Example: User Story 4

```bash
# 1) 先并行写四个测试（应全部失败）
Task: "T069 [P] [US4] Unit tests in backend/tests/unit/test_quiz_generation.py"
Task: "T070 [P] [US4] Contract tests in backend/tests/contract/test_quiz_contract.py"
Task: "T071 [P] [US4] Integration test in backend/tests/integration/test_quiz_lock.py"
Task: "T072 [P] [US4] Integration test in backend/tests/integration/test_quiz_flow.py"

# 2) 再并行写前端组件与接口封装
Task: "T080 [P] [US4] Create frontend/src/components/QuizQuestion.vue"
Task: "T081 [P] [US4] Create frontend/src/components/QuizResult.vue"
Task: "T079 [US4] Create frontend/src/api/quiz.ts"

# 3) 服务层必须顺序推进（同一文件）
Task: "T075 [US4] quiz_service.py part 1: build_questions + start_daily_quiz"
  → "T076 [US4] quiz_service.py part 2: record_daily_quiz_answer（答对禁止删除）"
  → "T077 [US4] quiz_service.py part 3: finish_attempt"
```

---

## Implementation Strategy

### MVP First（建议：US1 + US2 + US3）

1. 完成 Phase 1 Setup
2. 完成 Phase 2 Foundational（**阻塞项，必须全绿**）
3. 完成 Phase 3（US1 注册登录）→ 独立验证场景 A
4. 完成 Phase 4（US2 每日目标 + 首页）→ 独立验证场景 B
5. 完成 Phase 5（US3 今日学习 + 发音）→ 独立验证场景 C
6. **STOP and VALIDATE**：此时已是「能注册、能设目标、能背单词、能听发音」的可用最小闭环，可先部署试用

### Incremental Delivery

7. Phase 6（US4 测验）→ 场景 D/E —— 至此「学完即测」闭环成立
8. Phase 7（US5 错题本）→ 场景 F
9. Phase 8（US6 专项练习）→ 场景 G —— 至此三条硬性规则全部落地，产品完整
10. Phase 9（US7 响应式）+ Phase 10（US8 发音降级）→ 场景 H
11. Phase 11 Polish → 全量回归与场景 A–H 验收

### 硬性规则的回归护栏

- T072 与 T086 是三大约束的**回归护栏**：任何后续改动 MUST 保持「今日测验答对不删错题」与「跨日/重登/新词不清空错题」两条断言通过
- T096 断言专项练习答对为**唯一**删除路径；代码评审时 `wrong_words` 的 DELETE MUST 仅存在于 T097 所写分支

---

## Notes

- **实施状态（2026-09-28）**：T001–T120 中 109 条已完成（代码、迁移、测试、文档、Docker 均落地）；剩余 11 条为**人工验收类任务**（T042 / T051 / T068 / T084 / T094 / T101 / T105 / T110 / T117 / T118 / T119），需在浏览器按 `quickstart.md` 场景 A–H 走查并填写验收记录，另需实测 p95 与重启后数据一致性。同一链路已由 `backend/scripts/smoke_check.py` 自动化冒烟覆盖，可作验收前的快速自检。
- **词表规模**：T017 现为 **2096 条**（源 `aa.txt`，统一格式 `单词 | 词性.释义 | 例句`；已超过 spec 目标约 1600 条）。历史：`words.json` 648 条 → `a.txt` 541 条 → 现按 `aa.txt` 2096 条。
  替换方式：`python scripts/normalize_words.py <源文件>`（归一 + 去重）→ `python scripts/validate_word_seed.py`（体检）→ `python scripts/reset_words.py`（清理旧词表与学习/测验/错题数据，保留账号并自动备份）→ `alembic downgrade 001 && alembic upgrade head`（重新导入）；只追加不清理时可跳过 `reset_words.py`，直接 `alembic upgrade head`（002 按 `spelling` 幂等 upsert）。可上调 `MIN_WORD_COUNT` 下限。
- **例句取代旧"常用短语"**：新词表第三段为**例句**（英文句子 + 中文翻译），复用 `words.phrase` 字段；前端发音按钮文案为"例句发音"，朗读英文部分（中文不朗读）。`app/seed_words.py` 同时兼容旧格式（`单词 词性.释义 | 短语1；短语2`）。
- **新增产物**（tasks.md 未列出）：`backend/scripts/smoke_check.py`（端到端冒烟脚本）、`backend/src/app/seed_words.py`（统一格式解析）、`backend/scripts/normalize_words.py`（词表归一）、`backend/tests/**/__init__.py`（使 `tests` 包可被导入）。
- **音标为空**：用户词表不含音标，`words.phonetic` 全为 `NULL`，前端按"有音标才显示"处理（符合 FR-013）。
- **澄清结论落地（Session 2026-09-28 第二轮）**：
  1. 每日目标变更（FR-010）：当日已浏览 ≥ 1 → 集合不变、次日生效；当日尚未浏览 → **立即重算**（`study_service.reset_today_set_if_not_started`，由 `settings_service.update_settings` 触发；新增集成用例 `test_settings_flow.py`）。
  2. 短语发音（FR-015 / FR-016）：短语按 `；` 拆条展示，每条一个发音按钮且只朗读英文部分（前端 `utils/phrase.ts` + 后端 `pronounce_service.speakable_text` 双重剥离中文，长度上限放宽到 120）；学习页与错题本页一致。
  3. 测验题序（FR-024 补充）：题目仍覆盖当日全部单词，题序按本轮 attempt 随机洗牌（`quiz_service.shuffle_questions`），同一轮内稳定。
  4. 连带修复：专项练习同一题在一轮内"先答对后改答为错"会重新入本（以最后一次作答为准），`ReviewAnswerResponse` 新增 `added_back_to_wrong_words` 字段。
  5. `scripts/smoke_check.py` 改为每次使用新账号（`smoke_<时间戳>`），避免复用旧账号跳过测验锁定校验。
- **第二轮品牌与多设备需求（Session 2026-09-28 第三轮 specify）**：
  1. 产品名称统一为 **1+1=2**（FR-044）：`frontend/index.html` 的 `<title>` 与 `AppShell.vue` 页头已改为 `1+1=2`（T120 完成）；README 标题同步。
  2. 多设备访问（FR-042 扩展 + FR-045 ~ FR-049）：新增 T121–T124（平板横竖屏、触摸可达性、跨设备一致性、局域网访问），均为**人工实测类**，需按 `quickstart.md` 场景 H1b / H1c / H4 / H5 走查。
  3. 落地前提：服务需监听所有网卡（`uvicorn --host 0.0.0.0`）并在防火墙放行端口，Vite dev 已加 `host: true`；本版不做公网部署 / HTTPS / PWA。
- [P] = 不同文件、无未完成依赖；[Story] 标签用于追溯至 spec.md 的 US1–US8
- Setup / Foundational / Polish 阶段**不带** Story 标签
- 每个 Story 阶段先写测试并验证失败（章程 III），再实现
- 字段约束（长度、唯一、CHECK、枚举）已在任务描述中逐条引用 `data-model.md`，实现时不得自行放宽
- 迁移类任务（T016 / T019）为停机窗口，MUST 在任何读取新表的代码合并前完成
- 建议每个任务或逻辑分组完成后提交一次，遇到 Checkpoint 先独立验证再继续
