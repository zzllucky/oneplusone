# Phase 0 Research: 测验防误触

**Feature**: 005-quiz-mis-tap-guard | **Date**: 2026-10-19

目标：把 spec 中"防误触"落到可执行的技术决策，解决未知项并给出被否决的备选。

## R-001 用什么机制拦截"离开答题页"

**Decision**: 用 Vue Router 的**组件内离开守卫**（`onBeforeRouteLeave`），在三个答题页各自注册，由共用模块 `useQuizExitGuard` 实现。

**Rationale**:
- 拦截条件完全由页面自身状态决定，守卫写在页面里最内聚；
- 一次注册即可覆盖三类离开来源：底部导航 / 侧栏导航的路由链接点击、浏览器返回、手机返回手势；
- 不动 `AppShell.vue`，导航组件保持纯展示。

**Alternatives considered**:
- 全局前置守卫 `router.beforeEach`：需要把"是否答题中"提升到全局（store 或路由元信息），把页面状态外泄，耦合度更高 → 否决；
- 在 `AppShell` 的导航链接上拦截点击：无法覆盖浏览器返回与手势返回，而这两者同样会丢整轮 → 否决；
- 原生 `beforeunload` 弹窗：只在刷新/关闭时触发，且文案不可控 → 否决。

## R-002 如何判定"答题中"

**Decision**: `isActive = questions.length > 0 && !report`。三个答题页现有状态均为 `questions`（题目数组）、`currentIndex`、`result`（当前题作答结果）、`report`（结果页数据），判定式可直接复用。

**Rationale**:
- 未开始：`questions` 为空 → 不拦截（spec FR-007）；
- 答题中：`questions` 非空且 `report` 为空 → 拦截（spec FR-001）；
- 已出结果：`report` 非空 → 不拦截（spec FR-007）。

**Alternatives considered**: 以"是否已点开始"的独立布尔标记判定 —— 需新增状态且可能与 `questions` 不同步 → 否决；以后端是否存在未完成轮次判定 —— 需新增接口，超出本次范围 → 否决。

## R-003 确认弹窗的形态

**Decision**: 新建自包含组件 `ConfirmDialog.vue`（无依赖、纯展示、可单测），文案与按钮文案由 props 传入，选择结果通过事件回传。

**Rationale**: 项目无现成弹窗组件（`src/components` 下只有业务组件）；自研比引入 UI 库更符合"零新增依赖"，且样式与既有卡片风格一致、按钮可做大不易误触。

**Alternatives considered**:
- 浏览器原生 `confirm()`：改动最小，但样式不统一、手机端体验差、自动化测试无法断言 → 否决；
- 引入第三方弹窗/UI 库：为一次确认引入依赖，违反章程"依赖引入需论证" → 否决。

## R-004 切题后防连点的实现

**Decision**: 在 `QuizQuestion` 内部维护锁定窗口：监听题目变化（题目或索引变化）后进入锁定，300 毫秒后解锁；锁定期内选项点击直接返回，不触发提交事件。

**Rationale**: 锁定逻辑与选项渲染同处一个组件最内聚；锁定期内不触发提交事件，页面就不会调用答对/答错音效，音效行为天然不受影响。

**Alternatives considered**:
- 给选项加 `disabled`：锁定期会短暂变灰闪烁，且 disabled 的按钮在部分浏览器会吞掉点击事件 → 否决；
- CSS `pointer-events: none`：实现最简，但无法阻止键盘操作、可访问性差 → 否决；
- 在页面层做防抖：三个页面各写一份，重复且难测 → 否决。

**常量**: `QUIZ_OPTION_LOCK_MS = 300`（spec 允许 200–500 毫秒按实测微调，微调需同步更新契约与测试）。

## R-005 锁定窗口的范围

**Decision**: 只锁选项，不锁「下一题 / 查看结果」按钮。该按钮在页面层而非 `QuizQuestion` 内，结构上天然不受影响（spec FR-012）。

## R-006 守卫与弹窗的协作方式

**Decision**: 守卫在激活状态下同步返回 `false` 取消本次导航，并把目标路由暂存为待定项；用户点「继续答题」→ 清空待定项、留在原页；点「离开」→ 用目标路由主动跳转。待定项非空时再次触发离开一律返回 `false`，避免叠加弹窗。

**Rationale**: 路由守卫必须同步决策，因此先取消、后由用户显式放行是最简路径；暂存目标可保证「离开」跳到用户最初点的那一项（spec 边界：弹窗期间再点其他导航项不叠加）。

**Alternatives considered**: 守卫返回 Promise 等待用户选择 —— 弹窗与路由耦合、可测性差 → 否决。

## R-007 本轮作废如何落地

**Decision**: 不做任何服务端改动。「离开」即正常跳转，页面卸载后前端内存中的题目与进度随之丢弃；再次进入该页仍是未开始状态（现有逻辑：进入页面不自动开始）。已提交的作答记录保留在 `quiz_answers` 中，不受影响（spec FR-006、SC-004）。

**Rationale**: 现状已经是"未点完成即无结果页"，无需新增接口或状态清理；符合 spec 假设"作废沿用现有未完成轮次逻辑"。

## R-008 测试策略

**Decision**:
- 单元：`ConfirmDialog` 渲染与事件、`useQuizExitGuard` 拦截/放行/取消、`QuizQuestion` 锁定窗口（`vi.useFakeTimers()`）；
- 页面级（关键接缝）：三个答题页挂载真实路由（内存历史），验证"答题中点导航被拦 → 确认后跳转"与"未开始/结果页不拦"；
- 回归：既有 `QuizQuestion.spec.ts`、`quizSound.spec.ts`、`routeSound.spec.ts` 必须保持全绿（音效与判分不受影响）。

**Rationale**: 章程要求关键接缝用集成测试（真实路由而非 mock），且缺陷修复须先补可复现的失败测试。

## 未决项

无。spec 中两项 Outstanding（返回手势是否拦截、锁定窗口取值）已在 R-001 与 R-004 中以合理默认落定。
