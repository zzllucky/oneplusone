# Tasks: 学习音效反馈（Sound Effects）

**Input**: Design documents from `/specs/004-sound-effects/`

**Prerequisites**: [plan.md](./plan.md)（技术选型与结构）、[spec.md](./spec.md)（US1–US3 与 FR-001~FR-028）、[research.md](./research.md)（R-001~R-014）、[data-model.md](./data-model.md)、[contracts/sound-assets.md](./contracts/sound-assets.md)、[quickstart.md](./quickstart.md)

**Tests**: 本项目强制 TDD（constitution III），因此**测试任务先于实现任务，且必须先失败**。

**Organization**: 按 User Story 分组，每个 Story 可独立实现与验收。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可与同阶段其他 [P] 任务并行（不同文件、无未完成依赖）
- **[Story]**: 所属用户故事（US1/US2/US3）；Setup / Foundational / Polish 阶段无标签
- 描述中给出**确切文件路径**

## Path Conventions

Web 应用结构：`backend/scripts/`（音源生成脚本）、`frontend/src/`（前端源码）、`frontend/public/sounds/`（静态音源）、`frontend/tests/unit/`（Vitest 用例）。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 产出音源资产与生成能力（构建期一次性）

- [X] T001 [P] 新建音源生成脚本 `backend/scripts/generate_sound_assets.py`：按 [contracts/sound-assets.md](./contracts/sound-assets.md) 第 3 节的 18 条台词合成 mp3，支持 `--voice`（默认 `en-US-GuyNeural`）/ `--rate`（默认 `+15%`）/ `--pitch`（默认 `+8Hz`）/ `--out-dir`（默认 `frontend/public/sounds`），输出 `manifest.json`（`version=1`、含 `voice/rate/pitch` 与每个 `entries[]` 的 `event/file/text/duration_ms/bytes`），单条超时或失败即报错退出不写半成品；脚本顶部写清用途与"仅开发期使用、不进镜像"
- [X] T002 运行 T001 生成 `frontend/public/sounds/` 下 18 个 mp3 + `manifest.json`（**需联网**），并肉眼确认：18 条齐全、单条 `duration_ms ≤ 2000`、`bytes ≤ 30720`（30 KB）、总计 ≤ 300 KB

**Checkpoint**: 音源齐备，可支撑后续所有断言

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 自包含音效模块 + 发音让位查询，**必须先完成**（US1/US2/US3 全部依赖）

**⚠️ CRITICAL**: 测试先行 —— T003~T005 必须先跑一遍并**确认失败**，再动 T006~T008

- [X] T003 [P] 新建 `frontend/tests/unit/soundEvents.spec.ts`（资产契约测试，先失败）：校验事件映射覆盖契约第 3 节全部 18 个事件且无多余、与 `manifest.json` 事件集合完全一致、每个 `file` 在 `frontend/public/sounds/` 下存在且非空、`duration_ms ≤ 2000`、`bytes ≤ 30720`
- [X] T004 [P] 新建 `frontend/tests/unit/soundPreferences.spec.ts`（偏好测试，先失败）：默认 `{ enabled: false, volume: 70 }`；写入后读回一致（持久化）；损坏 JSON / 字段缺失 / `volume` 越界或非数字均回退默认值且不抛错；`volume=0` 时 `enabled` 仍为 `true`
- [X] T005 [P] 新建 `frontend/tests/unit/soundEffects.spec.ts`（播放与连对测试，先失败，mock `HTMLAudioElement`）：连对 1→10 依次解析为 `streak_1`…`streak_10`；第 11 题起为 `streak_extend`；答错解析为 `answer_wrong` 且计数归零；`reset()`（点开始）归零；`enabled=false` 时不调用 `play()`；发音进行中（`isPronouncing()` 为真）跳过本次且不补播；连续播放时先 `pause()` 再换 `src`（覆盖而非排队）；`play()` 抛错时静默降级（仅 `console.warn`）
- [X] T006 [P] 新建 `frontend/src/sounds/events.ts`：18 条事件 ↔ 台词 ↔ 文件映射（与契约第 3 节逐字一致），顶部注释说明"替换台词只改本文件"（FR-028）
- [X] T007 新建 `frontend/src/sounds/soundEffects.ts`（依赖 T006、T008）：`localStorage['word-study-sound-prefs']` 偏好读写（默认 `enabled=false`、`volume=70`）、单例播放器（覆盖播放、音量映射 `volume/100`、`preload='none'`）、连对计数（`onCorrect()`/`onWrong()`/`reset()`）、发音优先判断、失败静默降级；顶部注释写清模块职责与对外 API
- [X] T008 [P] 修改 `frontend/src/composables/useAudioWarmup.ts`：新增导出 `isPronouncing(): boolean`（共享发音播放器存在且未暂停即真），供 T007 让位判断（FR-026）
- [X] T009 跑 `cd frontend && npm test` 与 `npm run typecheck`，确认 Phase 2 全部通过（T003~T005 由红转绿）

**Checkpoint**: 音效模块可用且被测试锁住 —— 用户故事实现可以开始

---

## Phase 3: User Story 1 - 连续答对播报与答错复位 (Priority: P1) 🎯 MVP

**Goal**: 答题时按连对题数播放连杀台词（1–10）、连对 >10 播 `Good job`、答错播 `Storm the front.` 并复位、点"开始"播 `Come get some!` 并归零

**Independent Test**: 打开任意测验页 → 连答对 3 题依次听到 `First blood` / `Double kill` / `Triple kill`；答错听到 `Storm the front.`；再答对回到 `First blood`；连答对 12 题时第 11、12 题为 `Good job`

### Tests for User Story 1

- [X] T010 [US1] 新建 `frontend/tests/unit/quizSound.spec.ts`（组件级，@vue/test-utils + mock 播放）：答对触发 `streak_1`、连对到第 3 题为 `streak_3`、答错触发 `answer_wrong` 且下一次答对回到 `streak_1`、点击"开始"触发 `quiz.start` 并归零（三个测验页共用断言模板）

### Implementation for User Story 1

- [X] T011 [P] [US1] 修改 `frontend/src/pages/TodayQuizPage.vue`：`start()` 中播 `quiz.start` 并 `reset()` 连对；`select()` 拿到 `result.is_correct` 后调用 `onCorrect()` / `onWrong()`
- [X] T012 [P] [US1] 修改 `frontend/src/pages/ReviewQuizPage.vue`（错题本专项）：同 T011 的接入方式
- [X] T013 [P] [US1] 修改 `frontend/src/pages/ArchiveQuizPage.vue`（错题库专项）：同 T011 的接入方式
- [ ] T014 [US1] 人工验收 [quickstart.md](./quickstart.md) 场景 6、7、8、9、10：连杀 1–10 顺序正确、11+ 为 `Good job`、答错复位、重开一轮归零、快速连答不叠加且末次与实际连对数一致

**Checkpoint**: US1 独立完成并可演示（MVP）

---

## Phase 4: User Story 2 - 页面进入与"开始"语音 (Priority: P2)

**Goal**: 进入首页 / 学习 / 测验 / 错题 / 总结各播一句对应台词；专项练习页（`/review`、`/archive`）**进入不播**，仅在点"开始"时播 `Come get some!`

**Independent Test**: 依次进入五个页面各听到对应一句且不串台；进入 `/review`、`/archive` 无声；点开始听到 `Come get some!`

### Tests for User Story 2

- [X] T015 [US2] 新建 `frontend/tests/unit/routeSound.spec.ts`：白名单 5 个路径各触发一次对应 `page.*` 事件；`/review`、`/archive` 不触发任何 `page.*`；同一路径极短时间内重复进入只播一次（去重，FR-019）

### Implementation for User Story 2

- [X] T016 [US2] 修改 `frontend/src/router/index.ts`：在路由进入后按路径白名单（`/home`、`/study`、`/quiz`、`/wrong-words`、`/summary`）调用音效模块播放对应 `page.*`，并加极短时间去重窗口
- [ ] T017 [US2] 人工验收 [quickstart.md](./quickstart.md) 场景 3、4、5：五页各一句、专项页进入无声、点开始播 `Come get some!`

**Checkpoint**: US1 与 US2 各自独立可用

---

## Phase 5: User Story 3 - 音效开关与音量控制 (Priority: P3)

**Goal**: 设置页提供音效开关（**默认关闭**）与音量滑块（0–100，步进 10，默认 70），变更即时生效并留存本设备

**Independent Test**: 设置页关闭 → 全程无声；重开浏览器保持；再开启 → 声音恢复且音量生效

### Tests for User Story 3

- [X] T018 [US3] 新建 `frontend/tests/unit/settingsSound.spec.ts`：开关切换与音量变更即时写入 `localStorage['word-study-sound-prefs']`；首次挂载展示为关闭状态且音量为 70；读入非法值不崩溃并回退默认

### Implementation for User Story 3

- [X] T019 [US3] 修改 `frontend/src/pages/SettingsPage.vue`：在每日目标卡片之外新增「音效」卡片 —— 开关（默认关）+ 音量滑块（`min=0 max=100 step=10`，默认 70）+ 一句"开启后答题与进入页面会有英文语音"的说明；变更即时写入 localStorage（**不走后端接口**，FR-024）
- [ ] T020 [US3] 人工验收 [quickstart.md](./quickstart.md) 场景 1、2、12、14、15：默认无声、开启生效、刷新/重开保持、关闭后 0 次发声、音效关闭时无 `/sounds/` 请求

**Checkpoint**: 三个 User Story 全部独立可用

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 全量验证、文档、合规自查与发布

- [X] T021 [P] 跑全量校验：`cd frontend && npm test && npm run typecheck && npm run build`，并确认 `frontend/dist/sounds/` 含 18 个 mp3 + `manifest.json`
- [X] T022 [P] 更新 `CHANGELOG.md`：新增 `[0.3.0] - 2026-09-30` 条目（18 类事件语音反馈、默认关闭、音源随站点打包离线可用、后端零改动），并在顶部补回空 `[Unreleased]` 段
- [ ] T023 按 [quickstart.md](./quickstart.md) 执行**全量人工验收**（16 条场景逐条打勾），重点补场景 11（发音优先）、13（离线可用）、16（首屏增量 ≤1s）
- [X] T024 合规与回归自查：确认 `backend/src/` **零改动**（无新接口、无新字段、无迁移）、`frontend/package.json` **零新增依赖**、无埋点/无外部请求；回归 001/002/003（后端 `pytest` 全量 + 前端 `npm test` 全绿 + 手动走一遍学习→测验→总结）
- [X] T025 发布：前端构建产物按既有方式上线（Docker 镜像或 `deploy.tgz` 均自动含 `frontend/dist`），线上确认 `/sounds/streak_1.mp3` 可访问且页面音效正常

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**：无依赖，立即开始（T002 依赖 T001）
- **Foundational (Phase 2)**：依赖 Phase 1（契约测试要读真实 manifest 与 mp3）—— **阻塞所有 User Story**
- **User Stories (Phase 3–5)**：均依赖 Phase 2 完成；彼此可按优先级顺序或并行推进（US1 → US2 → US3）
- **Polish (Phase 6)**：依赖全部目标 User Story 完成

### User Story Dependencies

- **US1（P1）**：Phase 2 后即可开始，不依赖其他 Story（MVP）
- **US2（P2）**：Phase 2 后即可开始；与 US1 共用音效模块但互不阻塞
- **US3（P3）**：Phase 2 后即可开始；开关是前两者的闸门，建议与 US1 同期完成以便验收

### Within Each User Story

- 测试（T010/T015/T018）先写并确认失败 → 再实现（T011–T013 / T016 / T019）→ 人工验收（T014/T017/T020）
- 实现任务内部：页面/路由先接，再人工听感验收

### Parallel Opportunities

- Phase 1：T001 单独（T002 依赖它）
- Phase 2：T003 / T004 / T005 三个测试文件互不相同，可并行；T006 / T008 可并行；T007 依赖 T006 与 T008
- Phase 3：T011 / T012 / T013 三个页面文件互不相同，可并行；T010 可与之并行编写
- Phase 5：T018 与 T019 可并行

---

## Parallel Example: User Story 1

```bash
# 三个测验页并行接入（不同文件，无冲突）：
Task: "T011 [P] [US1] 修改 frontend/src/pages/TodayQuizPage.vue"
Task: "T012 [P] [US1] 修改 frontend/src/pages/ReviewQuizPage.vue"
Task: "T013 [P] [US1] 修改 frontend/src/pages/ArchiveQuizPage.vue"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup（T001、T002）—— 音源齐备
2. Phase 2 Foundational（T003–T009）—— 模块 + 测试锁定（**CRITICAL，阻塞后续**）
3. Phase 3 US1（T010–T014）—— 连杀播报与答错复位
4. **STOP and VALIDATE**：按 quickstart 场景 6–10 独立验收 US1
5. 可先上线 MVP（默认关闭，不影响未开启用户）

### Incremental Delivery

1. Setup + Foundational → 地基就绪
2. US1（连杀播报）→ 验收 → 可演示
3. US2（页面进入语音）→ 验收 → 可演示
4. US3（开关与音量）→ 验收 → 完整交付
5. Polish：全量验收 + CHANGELOG + 发布

### Parallel Team Strategy

多人协作时：Phase 1–2 一起完成后，A 做 US1、B 做 US2、C 做 US3（三者文件互不冲突）。

---

## Notes

- [P] = 不同文件、无未完成依赖；[Story] 标签用于追溯到 spec.md 的用户故事
- 每个 User Story 必须能独立实现、独立验收
- **测试必须先失败再实现**（constitution III）；音效的"好不好听、及不及时"只能人工判定，不假装自动化
- 音源生成（T002）**需要联网**，若离线则改用已生成的同名 mp3 手工补齐并同步 `manifest.json`
- 任务完成后停在每个 Checkpoint 做独立验证，再进入下一阶段
