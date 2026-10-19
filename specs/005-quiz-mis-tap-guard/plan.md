# Implementation Plan: 测验防误触（Quiz Mis-Tap Guard）

**Branch**: `005-quiz-mis-tap-guard` | **Date**: 2026-10-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-quiz-mis-tap-guard/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

学生用手机答题时，误触底部导航会整轮丢失；点「下一题」后的余下点击又会被判成选中下一题的选项。方案分两部分，均为纯前端改动：

1. **离开保护**：新增自包含模块 `useQuizExitGuard`（离开守卫）与 `ConfirmDialog`（确认弹窗），在三个答题页统一接入；答题进行中拦截离开（底部导航点击、浏览器返回、手机返回手势），弹出确认，选「继续答题」留在原题，选「离开」才跳转且本轮作废。
2. **防连点**：`QuizQuestion` 在题目切换后进入约 300 毫秒的锁定窗口，窗口内点击选项不提交、不发声，窗口结束立即恢复。

不新增后端接口与数据表，不新增第三方依赖，不改动既有答题流程与音效行为。

## Technical Context

**Language/Version**: TypeScript 5 / Vue 3（前端单页应用）；本次不涉及后端改动

**Primary Dependencies**: Vue 3、Vue Router 4、Pinia、Tailwind CSS（均为项目现有依赖）

**Storage**: 无新增存储；判定"答题中"仅用前端页面状态，服务端 `quiz_attempts` / `quiz_answers` 保持现状

**Testing**: Vitest + `@vue/test-utils` + jsdom（现有）；锁定窗口用 `vi.useFakeTimers()` 控制时间

**Target Platform**: 手机 / 平板 / 桌面浏览器（响应式：手机底部导航 56px 高，桌面为左侧栏导航，二者同为路由链接）

**Project Type**: Web 应用（前后端分离，本次仅前端）

**Performance Goals**: 弹窗出现与关闭无明显延迟；锁定窗口结束即可作答，正常答题节奏无可感知停顿

**Constraints**: 不引入任何第三方依赖；不新增服务端接口、数据表或字段；不改变既有答题、判分与音效行为；弹窗按钮触控区域与页面其他按钮一致

**Scale/Scope**: 3 个答题页接入 + 1 个新弹窗组件 + 1 个新守卫模块 + 1 处组件改动（选项锁定）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 条款 | 结论 | 说明 |
|---|---|---|
| I 库优先（模块自包含） | Pass | `ConfirmDialog` 只负责"展示确认与回传选择"；`useQuizExitGuard` 只负责"判定与拦截"；各自单一职责并自带测试 |
| II 契约先行 | Pass | 先出 `contracts/ui-guard.md`（组件 props/emits、守卫入参与返回、锁定常量），实现与测试同以其为事实来源 |
| III 测试先行 | Pass | 任务按 TDD 排序：先写失败测试（守卫拦截/放行、弹窗事件、锁定窗口），再实现 |
| IV 集成测试覆盖关键接缝 | Pass | 三个页面用真实路由（内存历史）做页面级测试，覆盖"守卫 ↔ 路由 ↔ 页面状态"接缝，不用 mock 掩盖接线 |
| V 简洁（YAGNI） | Pass | 仅两个新模块 + 一处组件改动；不引入弹窗库、不做"记住选择"等额外能力 |
| 附加约束 · spec 不含技术栈 | Pass | spec.md 只描述 what/why，技术选型只记录在本文件 |
| 附加约束 · 依赖引入需论证 | Pass | 零新增依赖，弹窗自研 |
| 附加约束 · 未成年数据合规 | Pass | 不新增收集字段、不涉及用户数据传输与存储 |

**Gate 结论**：无违规，无需填写 Complexity Tracking。

## Project Structure

### Documentation (this feature)

```text
specs/005-quiz-mis-tap-guard/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── ui-guard.md      # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   ├── ConfirmDialog.vue        # 新增：通用确认弹窗（自包含、可测）
│   │   └── QuizQuestion.vue         # 改动：增加切题锁定窗口
│   ├── composables/
│   │   └── useQuizExitGuard.ts      # 新增：答题中离开守卫（三页共用）
│   ├── pages/
│   │   ├── TodayQuizPage.vue        # 改动：接入守卫 + 弹窗
│   │   ├── ReviewQuizPage.vue       # 改动：接入守卫 + 弹窗
│   │   └── ArchiveQuizPage.vue      # 改动：接入守卫 + 弹窗
│   └── sounds/                      # 不涉及
└── tests/
    └── unit/
        ├── ConfirmDialog.spec.ts        # 新增
        ├── useQuizExitGuard.spec.ts     # 新增
        ├── quizExitGuardPages.spec.ts   # 新增：页面级（真实路由）
        └── QuizQuestion.spec.ts         # 改动：补充锁定窗口用例
```

**Structure Decision**: 沿用现有 frontend 单包结构（Option 2 的 frontend 部分）。守卫逻辑三页复用且需独立单测，故新增 `src/composables/`（与既有 `src/sounds/` 模块化风格一致）；弹窗为纯展示组件，放在既有 `src/components/`。本次不触碰 `backend/`。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

无违规，本节不适用。
