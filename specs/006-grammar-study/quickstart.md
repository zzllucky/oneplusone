# Quickstart: 初中英语语法学习（大纲 · 学卡 · 练习）

**Feature**: 006-grammar-study | **Date**: 2026-10-19
**用途**：端到端验证指南（跑通即证明功能可用）。实现细节见 `data-model.md`、`contracts/api.md` 与后续 `tasks.md`。

## Prerequisites

- Python 3.12+（后端）、Node 20+（前端构建）
- 已注册账号（语法页面沿用现有登录体系，无需新的注册字段）
- 不需要公网：语法学习无音频、无外部资源

## Setup

```bash
# 方式一：Docker Compose
docker compose up --build      # 访问 http://localhost:8000

# 方式二：本地开发
cd backend
uv sync --extra dev
alembic upgrade head            # 建表 + 词表种子 + 语法种子（迁移 006/007）
uvicorn app.main:app --reload --port 8000

cd frontend
npm install && npm run dev      # http://localhost:5173
```

## Test Commands

```bash
cd backend
uv run --extra dev pytest -q                                  # 全量（含单词模块回归）
uv run --extra dev pytest -q -k grammar                       # 语法相关单元 / 契约 / 集成

cd frontend
npm run test                    # Vitest（含新增语法组件与 store）
npm run typecheck               # vue-tsc
```

---

## 场景 A：语法大纲浏览与进度

| # | 步骤 | 预期 |
|---|---|---|
| A1 | 登录后从导航进入「语法」 | 进入 `/grammar`，看到 21 个模块分组（8 大时态 → 2 大语态 → 2 大非谓语 → 6 大实词 → 3 大从句）下的全部知识点 |
| A2 | 查看任一知识点条目 | 显示标题、深度标签（核心 / 了解）与状态徽章；全新账号全部为"未学" |
| A3 | 查看顶部计数 | 显示"已掌握 0 / 全部 82"，与实际一致 |
| A4 | 点击某知识点 | 进入该知识点的学卡页 `/grammar/{point_id}` |
| A5 | 换设备 / 重新登录同一账号 | 大纲进度完全一致（FR-019） |

---

## 场景 B：学卡学习 —— 猜一猜 → 讲解 → 学后检测（全对）

| # | 步骤 | 预期 |
|---|---|---|
| B1 | 打开一个未学知识点的学卡 | 先看到"猜一猜"：两个例句 + 问题 + 选项 |
| B2 | 任选一个选项（例如 B） | 立即显示针对 B 的解释性反馈（对错都解释原因），不显示"正确答案"判定 |
| B3 | 进入讲解 | 按卡面类型渲染：规则型显示规则 / 信号词 / 公式 / 锚例句 / 陷阱对照；对比型显示对比表；速记型显示口诀 |
| B4 | 进入学后检测并逐题作答 | 每题提交后立即看到对错、正确选项与解析；答错时额外看到所选错项的错因 |
| B5 | 三题全部答对并结算 | 显示本轮结果（3 题 / 答对 3 / 正确率 100% / 用时），知识点状态变为"已掌握" |
| B6 | 返回大纲页 | 该知识点显示"已掌握"徽章，顶部"已掌握 / 全部"计数 +1 |

---

## 场景 C：学卡学习 —— 未全对 / 只看不测

| # | 步骤 | 预期 |
|---|---|---|
| C1 | 在学后检测中故意答错一题后结算 | 结果为"未全对"，知识点状态保持"学习中"，不标记掌握 |
| C2 | 答错后查看语法错题本 | 该知识点已出现在错题本（场景 E） |
| C3 | 打开另一个未学知识点，只看讲解与猜一猜，不做检测就返回 | 状态为"学习中"（已学未测），不是"已掌握"（FR-006） |

---

## 场景 D：题库练习与即时判分

| # | 步骤 | 预期 |
|---|---|---|
| D1 | 在学卡页（或大纲条目）发起该知识点的练习 | 进入 `/grammar/{point_id}/practice`，按 L1 → L2 → L3 顺序拿到题目 |
| D2 | 逐题作答 | 每题提交后立即看到对错、正确选项、解析；答错显示所选选项的错因 |
| D3 | 答完全部题目并结算 | 显示总题数、答对数、答错数、正确率与用时 |
| D4 | 中途退出后再发起练习 | 可以重新开始一轮，不恢复上一轮未答题目 |
| D5 | 对"只有卡内检测题、无题库题"的知识点发起练习 | 明确提示"该知识点暂无练习题"（409 `no_grammar_questions`），不出现空白练习页 |
| D6 | 练习结算后查看该知识点掌握状态 | 保持结算前状态：练习不改变掌握状态（R-002） |

---

## 场景 E：语法错题本与回链重学

| # | 步骤 | 预期 |
|---|---|---|
| E1 | 在练习（或学后检测）中答错一题 | 判分返回中 `added_to_wrong_points=true`（首次） |
| E2 | 打开语法错题本 | 该知识点在列，显示所属模块、累计答错次数、连续答对次数、加入时间 |
| E3 | 点击该错题条目 | 直达该知识点的学卡页，可重新学习 |
| E4 | 再次练习该知识点并连续答对 2 题 | 第 2 题判分返回 `removed_from_wrong_points=true`，错题本中该条目消失 |
| E5 | 连续答对中途又答错一次 | 连续答对次数归零，需重新累计 2 次才移出 |
| E6 | 同一知识点多次答错 | 累计答错次数递增，加入时间保持首次不变 |

---

## 场景 F：边界与保护

| # | 步骤 | 预期 |
|---|---|---|
| F1 | 退出登录后直接访问 `/grammar`、`/grammar/G-A01` | 重定向到登录页，登录后回到原目标 |
| F2 | 请求不存在的知识点 `GET /api/grammar/points/G-ZZZ` | 404 `grammar_point_not_found` |
| F3 | 同一轮次内对同一题重复提交答案 | 返回首次结果，计数与错题次数不重复累加（FR-015） |
| F4 | 对已结算轮次再次作答 / 再次结算 | 409 `grammar_attempt_already_finished`，统计不变 |
| F5 | 提交不属于该题的选项键（如 `E`） | 422 `invalid_choice_key` |
| F6 | 直接调用出题接口查看响应体 | 响应中不含 `is_correct`、`correct_key`、`explanation`、`feedback`（FR-007） |
| F7 | 语法错题本为空时打开 | 显示空状态引导，不报错 |

---

## 场景 G：跨端与视口

| # | 步骤 | 预期 |
|---|---|---|
| G1 | 在 360 / 768 / 1440 三种视口打开大纲页、学卡页、练习页 | 三页均完整可用，无横向滚动、无元素溢出 |
| G2 | 窄屏（<768）查看导航 | 底部导航含「语法」入口，点击区域满足触摸操作 |
| G3 | 在手机与电脑分别练习同一账号 | 进度、掌握状态、语法错题本完全一致 |

---

## 场景 H：与单词模块互不干扰

| # | 步骤 | 预期 |
|---|---|---|
| H1 | 先记录单词模块的每日目标、今日进度与单词错题本 | 作为基线 |
| H2 | 完成一轮语法学习、练习与错题回链 | 语法侧数据正常写入 |
| H3 | 回到单词模块查看 | 每日目标、今日集合、测验解锁状态、单词错题本与基线完全一致（FR-020） |
| H4 | 运行全量后端测试 | 单词模块既有测试全部保持通过 |

---

## 走查记录（2026-10-19 实现后）

自动化覆盖（`uv run --extra dev pytest -k grammar` + `npm run test`，共 47 后端 + 10 前端用例）：

| 场景 | 结论 | 依据 |
|---|---|---|
| A1–A4 | 通过 | 契约 `test_outline_shape`、集成 `test_card_study_flow_marks_mastered` |
| A5 | 通过 | 单元 `test_outline_isolated_between_users`、集成 `test_grammar_data_isolated_between_accounts` |
| B1–B2 | 通过 | 契约 `test_point_card_shape_and_answer_protection`（payload 无 answer/feedback）、`test_guess_feedback_after_choice`、前端 `grammarCard.spec.ts` |
| B3 | 通过（代码审查） | 学卡页按 `card_type` 渲染 rule / contrast / memorize 三个分支 |
| B4–B6 | 通过 | 集成 `test_card_study_flow_marks_mastered`（全对 → 已掌握 + 计数 +1） |
| C1–C3 | 通过 | 单元 `test_card_attempt_with_wrong_answer_keeps_learning`、`test_mark_viewed_sets_learning_and_is_idempotent` |
| D1–D4 | 通过 | 集成 `test_practice_flow_and_restart`、单元 `test_bank_attempt_orders_by_level_then_index` |
| D5 | 通过 | 契约 `test_practice_start_without_questions`、前端练习页提示态 |
| D6 | 通过 | 单元 `test_bank_finish_does_not_change_status` |
| E1–E6 | 通过 | 单元 `test_wrong_point_insert_then_accumulate` / `..._removed_after_streak` / `..._streak_resets_on_wrong`、集成 `test_wrong_point_closed_loop` |
| F1 | 通过 | 契约 9 端点未登录 401 + 前端路由守卫（既有 `meta.public` 机制） |
| F2–F6 | 通过 | 契约 `test_point_card_not_found`、`test_answer_invalid_choice_key_and_idempotent`、`test_answer_and_finish_flow`、答案保护递归断言 |
| F7 | 通过 | 契约 `test_wrong_points_empty`、前端空状态 |
| G1–G2 | 部分 | jsdom 无真实布局，以结构约束测试替代（`grammarResponsive.spec.ts`）；**待人工**在 360/768/1440 真实浏览器核对 |
| G3 | 通过 | 同 A5（账号隔离） |
| H1–H4 | 通过 | 全量 `pytest` 265 通过（基线 218 全绿，新增 47）；语法未改动任何既有迁移 |

**遗留待人工验证**：G1 三种视口的真实渲染（无横向滚动 / 无元素溢出）、B3 三种卡型的教研内容观感。
