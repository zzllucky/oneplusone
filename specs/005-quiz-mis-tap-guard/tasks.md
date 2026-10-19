---

description: "Task list for 测验防误触（005-quiz-mis-tap-guard）"
---

# Tasks: 测验防误触（Quiz Mis-Tap Guard）

**Input**: Design documents from `/specs/005-quiz-mis-tap-guard/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/ui-guard.md, quickstart.md

**Tests**: 章程第 III 条强制 TDD —— 每个模块先写失败测试，确认失败后再实现，实现后转通过

**Organization**: 按用户故事分组；共用模块（弹窗、守卫、选项锁定）放在 Foundational 阶段，因为它们同时服务 US1 与 US2

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 所属用户故事（US1 / US2）
- 描述中给出确切文件路径

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 准备模块位置与验证基线

- [x] T001 创建 `frontend/src/composables/` 目录（守卫模块位置），并跑一次 `cd frontend && npm test` 记录当前全绿基线（48 例）以便区分新增失败

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 三个共用模块（确认弹窗、离开守卫、选项锁定）—— US1 与 US2 都依赖它们

**⚠️ CRITICAL**: 本阶段未完成前，不得开始任何用户故事的页面接入工作

**契约事实来源**：`specs/005-quiz-mis-tap-guard/contracts/ui-guard.md`（CD-1~CD-5、EG-1~EG-5、LK-1~LK-6）

### 测试先行（创建后必须失败）

- [x] T002 [P] 按 CD-1~CD-5 写 `frontend/tests/unit/ConfirmDialog.spec.ts`（渲染/文案/`confirm` 与 `cancel` 事件/对话框语义与按钮尺寸），此时组件不存在，用例应失败
- [x] T003 [P] 按 EG-1~EG-5 写 `frontend/tests/unit/useQuizExitGuard.spec.ts`（激活时记录目标并取消导航、重复触发不覆盖、未激活放行、取消后停留、确认后跳转），此时模块不存在，用例应失败
- [x] T004 [P] 按 LK-1~LK-6 在 `frontend/tests/unit/QuizQuestion.spec.ts` 追加锁定窗口用例（切题后 300ms 内点击不触发 `select`、窗口结束后正常触发、窗口内点击不补提交、锁定不改变视觉禁用态），用 `vi.useFakeTimers()` 控时，此时用例应失败

### 实现（使上述测试转通过）

- [x] T005 实现 `frontend/src/components/ConfirmDialog.vue`：`props` 为 `open/title/message/confirmText/cancelText`，`emits` 为 `confirm/cancel`，`open=false` 不渲染，`role="dialog"` + `aria-modal`，两个按钮点击区域不小于 44×44，样式沿用现有 `card` 与 `btn-primary` / `btn-ghost`
- [x] T006 实现 `frontend/src/composables/useQuizExitGuard.ts`：入参 `{ isActive: () => boolean }`，返回 `{ pending, confirmLeave, cancelLeave }`，内部注册 `onBeforeRouteLeave`；激活且 `pending` 为空时记录 `to.fullPath` 并返回 `false`，`pending` 非空时保持原值并返回 `false`，未激活时放行
- [x] T007 在 `frontend/src/components/QuizQuestion.vue` 增加选项锁定：新增 `lockMs` prop（默认 `QUIZ_OPTION_LOCK_MS = 300`，可调区间 200–500），监听题目或题序号变化后进入锁定窗口、到时解锁；锁定期内点击选项直接返回且不 `emit('select')`，同时不改变选项的视觉禁用态

---

## Phase 3: User Story 1 (P1) — 答题进行中离开需二次确认

**Goal**: 三个答题页答题进行中点导航 / 返回时弹二次确认；「继续答题」留在原题，「离开」才跳转且本轮作废；未开始与结果页不弹

**Independent Test**: 在今日测验页答 2 题后点底部「首页」 → 弹窗出现且不跳走 → 点「继续答题」仍在原第 3 题 → 再点导航并选「离开」 → 跳到首页，回到测验页需重新开始

- [x] T008 [US1] 写页面级测试 `frontend/tests/unit/quizExitGuardPages.spec.ts`：用真实路由（内存历史）挂载 `TodayQuizPage` / `ReviewQuizPage` / `ArchiveQuizPage`，覆盖验收场景 1–8（答题中点导航被拦、继续后停留、离开后跳转、未开始与结果页不拦、非答题页不受影响、返回操作同样拦截），此时应失败
- [x] T009 [P] [US1] `frontend/src/pages/TodayQuizPage.vue` 接入守卫与弹窗：`isActive = questions.length > 0 && !report`，弹窗文案严格用契约值（标题"离开测验？"、正文"离开后本轮测验不会保留，确定离开吗？"、主按钮"继续答题"、次按钮"离开"）
- [x] T010 [P] [US1] `frontend/src/pages/ReviewQuizPage.vue` 同样接入（同一判定式与同一文案）
- [x] T011 [P] [US1] `frontend/src/pages/ArchiveQuizPage.vue` 同样接入（同一判定式与同一文案）
- [x] T012 [US1] 跑 `cd frontend && npm test` 与 `npm run typecheck`，确认 T008 的用例转通过且既有 48 例无回归

---

## Phase 4: User Story 2 (P2) — 切题后选项防连点

**Goal**: 点「下一题」进入新题的极短时间内，选项点击不提交、不发声；窗口结束立即恢复

**Independent Test**: 答完一题后快速连点「下一题」位置 2–3 次 → 无答案提交、无对错反馈与音效；等待约 0.3 秒后点选项 → 正常作答

- [x] T013 [US2] 在 `frontend/tests/unit/quizExitGuardPages.spec.ts` 追加页面级用例：答完一题点「下一题」后立即点击选项不提交且无音效调用；推进假定时器后再点击则正常提交（「下一题」按钮本身不受锁定影响）
- [x] T014 [US2] 回归验证：`frontend/tests/unit/quizSound.spec.ts`、`routeSound.spec.ts`、`soundEvents.spec.ts` 保持全绿，确认锁定与守卫未影响音效与判分行为

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T015 跑 `cd frontend && npm run typecheck && npm test && npm run build`，三者均通过
- [x] T016 按 `specs/005-quiz-mis-tap-guard/quickstart.md` 执行端到端人工验收（场景 A–G，手机底部导航与桌面侧栏各一遍），记录结果；若 300ms 在真机上手感不符，在 200–500 区间调整并同步 `contracts/ui-guard.md`、`data-model.md` 与相关测试
- [x] T017 构建产物后按既有发布流程更新线上（`npm run build` → 打包上传 → 重启服务），冒烟 `/api/health` 与三个答题页

---

## Dependencies

- Phase 1 → Phase 2：模块目录与测试基线
- Phase 2 → Phase 3 / Phase 4：弹窗、守卫、锁定必须先可用
- US1（Phase 3）可在 US2（Phase 4）之前独立完成并交付（锁定实现在 T007，US2 只补页面级验证）
- Phase 5 依赖 Phase 3 与 Phase 4 完成

### Story Completion Order

1. **US1 (P1)**：整轮丢失是最大损失，MVP 即此
2. **US2 (P2)**：误选单个选项，损失次之

### Within Each User Story

- 测试先写并确认失败 → 实现 → 测试转通过 → 重构
- 共用模块（T005–T007）先完成，页面接入其后
- 每个故事完成后独立验证，再进入下一个

### Parallel Opportunities

- Phase 2 的 T002 / T003 / T004 三个测试文件互不冲突，可并行编写
- Phase 3 的 T009 / T010 / T011 是三个不同页面文件，可并行接入
- Phase 3 与 Phase 4 在 T007 完成后可并行推进

---

## Parallel Example: User Story 1

```bash
# 三个页面接入可同时进行
Task: "T009 [US1] TodayQuizPage.vue 接入守卫与弹窗"
Task: "T010 [US1] ReviewQuizPage.vue 接入守卫与弹窗"
Task: "T011 [US1] ArchiveQuizPage.vue 接入守卫与弹窗"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1 Setup
2. 完成 Phase 2 Foundational（弹窗 + 守卫 + 锁定）
3. 完成 Phase 3 User Story 1
4. **STOP and VALIDATE**：按 quickstart 场景 A–D、F、G 验证
5. 可先部署/演示（此时已解决"误触丢整轮"）

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. + US1 → 独立验证 → 可交付（MVP）
3. + US2 → 独立验证 → 完整防误触
4. Polish（typecheck / 构建 / 真机走查 / 发布）

### Parallel Team Strategy

多人协作时：Phase 2 后，A 做三个页面接入（US1），B 做页面级防连点验证与回归（US2）。

---

## Notes

- [P] 任务 = 不同文件、无依赖；同一文件的多个改动不得并行
- 文案与常量以 `contracts/ui-guard.md` 为唯一事实来源，实现期不得自行改写
- 锁定期内不 `emit('select')` 是"不发声"的关键：音效由页面在作答后调用，不提交即不发声
- 每完成一个任务或一组相关任务即提交一次，便于回滚
- 任何一步测试未全绿，不得进入下一任务（章程质量门）
