# Data Model: 学习日历总结

**Feature**: `002-study-calendar-summary` | **Date**: 2026-09-30

## 总原则：不新增业务表

本功能**只做只读聚合**：所有数字都从既有表按"用户 + 日期"聚合得出，**不落地任何汇总表、不新增任何个人信息字段**（research R-001 / R-007）。唯一的存储变更是迁移 `005` 新增 3 个**查询索引**。

因此下文描述的"每日汇总 / 月度汇总"是**派生视图**，不是数据库实体；它们的口径即接口返回值的口径（`contracts/api.md`）。

## 派生实体

### 1. 每日汇总（Daily Summary）—— 不落库

同一账号同一日仅一份（由聚合键 `(user_id, date)` 唯一确定）。

| 字段 | 类型 | 口径（来源） |
|---|---|---|
| `date` | date | 聚合键；Asia/Shanghai 日期 |
| `has_record` | bool | 该日存在 `daily_sets` 记录，或存在任何学习 / 测验 / 练习行为 |
| `level` | enum `gray` / `light` / `deep` | `gray` = 无 `daily_sets` 记录；`light` = 有记录但无学习行为；`deep` = 有学习行为（FR-019） |
| `shade` | int 0–3 | `gray`/`light` = 0；`deep` 按学习词数分档：`1–9` → 1、`10–29` → 2、`≥30` → 3（FR-019） |
| `learned_count` | int | `daily_sets.study_date = date` 下 `daily_set_items.viewed_at IS NOT NULL` 的条目数（FR-006） |
| `quiz.rounds` | int | 当天完成的今日测验次数 = 上述范围内 `COUNT(*)`（即已完成 attempt 的条数） |
| `quiz.answered` / `correct` / `wrong` | int | `quiz_attempts`：`kind='daily' AND study_date = date AND finished_at IS NOT NULL` 的 `total_count` / `correct_count` / `wrong_count`（FR-008） |
| `quiz.completed` | bool | 存在上述已完成 attempt |
| `review_practice.rounds` | int | `quiz_answers ⋈ quiz_attempts(kind='review')` 中 `answered_at` 落在该日的 `COUNT(DISTINCT attempt_id)`（FR-009） |
| `review_practice.answered` / `correct` / `wrong` | int | 同上范围内 `COUNT(*)` / `SUM(is_correct)` / `COUNT(*) - SUM(is_correct)` |
| `archive_practice.*` | 同前 | `kind='archive'`（FR-010） |

**"有学习行为"的定义**（决定 `light` 与 `deep`）：`learned_count > 0` 或 `quiz.completed` 或 `review_practice.answered > 0` 或 `archive_practice.answered > 0`。

### 2. 月度汇总（Monthly Total）—— 不落库

由该月各日汇总加总（FR-022），**不含在线时长**：

| 字段 | 口径 |
|---|---|
| `learned_words` | `SUM(learned_count)` |
| `quiz.rounds` / `answered` / `correct` / `wrong` | 该月各日 `quiz` 汇总 |
| `review_practice.*` | 该月各日 `review_practice` 汇总 |
| `archive_practice.*` | 该月各日 `archive_practice` 汇总 |
| `active_days` | 该月 `has_record = true` 的天数 |

### 3. 连续学习天数（Streak）

- 口径：从**最近一个有学习行为的日期**往前连续计数（`deep` 天的连续段）；当天尚未学习时，**从昨天开始数**，不显示为 0（FR-023 / US4 验收 4）。
- 中断一天后重新计数（US4 验收 5）；当月无任何活动时为 0（US4 验收 6）。
- 实现：一次性取出该用户所有"有学习行为的日期"集合（去重、排序），取最长连续段末端计算；不按天循环查询。

## 既有表（只读引用，字段以代码为准）

| 表 | 用到的字段 | 约束 / 备注 |
|---|---|---|
| `daily_sets` | `id`, `user_id`, `study_date`, `created_at` | `UNIQUE(user_id, study_date)`；打开首页 / 学习页即生成（浅绿判定依据） |
| `daily_set_items` | `id`, `daily_set_id`, `word_id`, `viewed_at` | `viewed_at` NULL = 未浏览；自身无 `user_id`，必须 join `daily_sets` |
| `quiz_attempts` | `id`, `user_id`, `kind('daily'`\|`'review'`\|`'archive')`, `study_date`, `started_at`, `finished_at`, `total_count`, `correct_count`, `wrong_count` | `kind='daily'` 才有 `study_date`；`finished_at` 非空 = 已完成 |
| `quiz_answers` | `id`, `attempt_id`, `word_id`, `is_correct`, `answered_at` | `UNIQUE(attempt_id, word_id)`；同一题重答以最后一次为准 |
| `users` | `id`, `created_at` | 注册前的日期一律为 `gray` |
| `user_settings` | `user_id`, `daily_goal` | 仅用于展示，不参与聚合 |

时间口径：所有 `datetime` 为 **naive UTC**，按 `settings.timezone = "Asia/Shanghai"` 换算归日（FR-013）。

## 枚举与不变量

- `level ∈ {gray, light, deep}`；`shade ∈ {0,1,2,3}`，且 `level != deep ⇒ shade = 0`。
- 未来日期、注册前日期：一律 `level=gray`、`has_record=false`、各项为 0；点击时前端提示"当天没有学习记录"（US3）。
- 同一天多轮专项练习：累加，不覆盖（FR-012）。
- 聚合结果为**只读**：本功能不写入、不修改、不删除任何既有数据。

## 迁移 `005_summary_query_indexes`

**upgrade**：仅创建索引，不建表、不改字段、不回填数据：

| 索引 | 列 | 用途 |
|---|---|---|
| `ix_quiz_attempts_user_kind_date` | `quiz_attempts(user_id, kind, study_date)` | 按月查今日测验 |
| `ix_quiz_attempts_user_finished` | `quiz_attempts(user_id, finished_at)` | 按完成时间兜底 / 已完成轮次筛选 |
| `ix_quiz_answers_answered_at` | `quiz_answers(answered_at)` | 专项练习按作答时刻归日的范围扫描 |

**downgrade**：删除上述 3 个索引。

> 注意：SQLite 的部分索引 / 表达式索引在 Alembic 下需谨慎（003 曾因 `sqlite_where` 传裸字符串导致 `AttributeError` 且索引静默丢失）。本迁移只用普通列索引，不使用 `sqlite_where`；仍需在测试中断言索引真实存在于 `sqlite_master`。
