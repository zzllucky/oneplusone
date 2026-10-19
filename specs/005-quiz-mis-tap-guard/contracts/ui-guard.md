# Contract: 防误触 UI 模块契约

**Feature**: 005-quiz-mis-tap-guard | **Date**: 2026-10-19 | **Source of truth**: 实现与测试同以此文件为准

本功能对外暴露三个模块边界：确认弹窗、离开守卫、选项锁定。三者互不依赖业务判分逻辑。

## 1. ConfirmDialog（确认弹窗）

**职责**：展示一句提示与两个按钮，把用户选择回传给调用方。不做任何业务判断。

```ts
interface ConfirmDialogProps {
  open: boolean          // 是否显示
  title: string          // 弹窗标题
  message: string        // 提示正文
  confirmText: string    // 次按钮文案（离开）
  cancelText: string     // 主按钮文案（继续答题）
}

interface ConfirmDialogEmits {
  (e: 'confirm'): void   // 点击"离开"
  (e: 'cancel'): void    // 点击"继续答题"
}
```

行为契约：

| 编号 | 条件 | 期望 |
|---|---|---|
| CD-1 | `open === false` | 不渲染任何弹窗内容 |
| CD-2 | `open === true` | 渲染 `title`、`message` 与两个按钮，文案与 props 一致 |
| CD-3 | 点击"离开" | 触发 `confirm` 事件一次，不触发 `cancel` |
| CD-4 | 点击"继续答题" | 触发 `cancel` 事件一次，不触发 `confirm` |
| CD-5 | 弹窗可见 | 具备对话框语义（`role="dialog"` 与 `aria-modal`），两个按钮点击区域不小于 44×44 |

## 2. useQuizExitGuard（离开守卫）

**职责**：在答题进行中拦截离开，暂存目标路由并把最终决定交回页面；非答题中不干预。

```ts
interface UseQuizExitGuardOptions {
  isActive: () => boolean   // 是否处于答题中（由页面状态计算）
}

interface UseQuizExitGuardResult {
  pending: Readonly<Ref<string | null>>  // 待定目标路由（fullPath），无则为 null
  confirmLeave: () => Promise<void>      // 确认离开：跳往待定目标并清空
  cancelLeave: () => void                // 继续答题：仅清空待定目标
}
```

行为契约（路由离开守卫内）：

| 编号 | 条件 | 期望 |
|---|---|---|
| EG-1 | `isActive() === true` 且 `pending === null` | 记录目标 `fullPath` 到 `pending`，取消本次导航 |
| EG-2 | `isActive() === true` 且 `pending !== null` | 保持原 `pending` 不变，取消本次导航（不叠加、不覆盖目标） |
| EG-3 | `isActive() === false` | 不记录，正常放行 |
| EG-4 | 调用 `cancelLeave()` | `pending` 置空，停留当前页，页面状态（题目、已答进度）完全不变 |
| EG-5 | 调用 `confirmLeave()` | 跳往 `pending` 指向的目标路由，随后 `pending` 置空 |

覆盖范围：底部导航 / 侧栏导航的路由链接点击、浏览器返回、手机返回手势，均由同一守卫处理。

## 3. QuizQuestion 选项锁定

**职责**：切题后的极短时间内忽略选项点击，避免连点误选。

```ts
interface QuizQuestionProps {
  question: QuizQuestion          // 既有：题目
  index: number                   // 既有：题序号
  total: number                   // 既有：总题数
  result?: { is_correct: boolean; correct_index: number } | null  // 既有
  lockMs?: number                 // 新增：锁定窗口，默认 QUIZ_OPTION_LOCK_MS
}
```

行为契约：

| 编号 | 条件 | 期望 |
|---|---|---|
| LK-1 | 题目或题序号发生变化 | 进入锁定窗口，持续 `lockMs`（默认 300）毫秒 |
| LK-2 | 锁定窗口内点击选项 | 不触发 `select` 事件，不改动作答状态、不触发音效 |
| LK-3 | 锁定窗口结束后点击选项 | 正常触发 `select`，行为与锁定前一致 |
| LK-4 | 锁定窗口内的点击 | 不在窗口结束后"补提交"，该次点击作废 |
| LK-5 | 已作答（既有 `disabled`）与锁定 | 两者互不影响；锁定不得改变选项视觉状态（不闪烁变灰） |
| LK-6 | 「下一题 / 查看结果」按钮 | 位于页面层，不受锁定窗口影响 |

## 4. 常量与文案

| 项 | 值 |
|---|---|
| `QUIZ_OPTION_LOCK_MS` | `300`（可调区间 200–500，改动需同步本契约与测试） |
| 弹窗标题 | 离开测验？ |
| 弹窗正文 | 离开后本轮测验不会保留，确定离开吗？ |
| 主按钮（继续） | 继续答题 |
| 次按钮（离开） | 离开 |

三个答题页（今日测验 / 错题专项 / 错题库专项）必须使用同一套文案与同一常量值，行为一致。
