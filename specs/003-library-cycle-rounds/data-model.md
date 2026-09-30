# Data Model: 词库循环学习与轮次统计

**Feature**: `003-library-cycle-rounds` | **Date**: 2026-09-29 | **Spec**: [spec.md](./spec.md)

## 新增实体

### `study_rounds` —— 学习轮次

某账号对词库的一次完整遍历（一轮）。**每个账号同一时刻最多一行「进行中」**（`completed_at IS NULL`）。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `user_id` | INTEGER | FK → `users.id` ON DELETE CASCADE, NOT NULL | 所属账号 |
| `round_no` | INTEGER | NOT NULL, ≥ 1 | 轮序号，同一账号内从 1 递增 |
| `cursor_word_id` | INTEGER | NOT NULL | **下一个待分配**的单词 id（游标）；按 `Word.id` 升序推进 |
| `started_on` | DATE | NOT NULL | 本轮开始日期（服务端"当日"口径） |
| `covered_at` | DATETIME | NULL | 本轮**已覆盖**时刻：游标越过词库最后一个单词（该日单词已分配完） |
| `completed_at` | DATETIME | NULL | 本轮**已完成**时刻：已覆盖且轮末当日测验完成；补记（FR-014）时也写此列 |

约束与索引：

- `UNIQUE (user_id, round_no)` —— 轮序号不重复。
- **部分唯一索引** `uq_study_rounds_open`：`UNIQUE (user_id) WHERE completed_at IS NULL` —— 保证同一账号只有一个进行中的轮次（SQLite 支持部分索引）。
- `INDEX (user_id, completed_at)` —— 便于统计"已完成轮数"。

### 派生数据（不单独建表）

- **已完成轮数** = `COUNT(study_rounds WHERE user_id = ? AND completed_at IS NOT NULL)`。
- **当前轮进度** = 本轮已学单词数 / 词库总数。**口径统一为游标推算**（唯一来源，不按 `daily_set_items` 计数）：
  `learned_count = COUNT(words WHERE id < cursor_word_id)`（每轮都从词库最小 `Word.id` 归位开始，故无需再减基线）。
  说明：改每日目标会重算当日集合，若按 `daily_set_items` 计数会出现"已学数回退/漂移"，因此以游标为准；已分配即计入，与契约中"已进入当日集合的单词数"一致。
- **词库总数** = `COUNT(words)`（当前 2096），随词表种子变化。

## 状态机

```text
                (创建 round_no = N)
                        │
                        ▼
                  ┌───────────┐
                  │  进行中   │  cursor <= max(Word.id)
                  └─────┬─────┘
     分配完最后一个单词 │ cursor > max(Word.id)
                        ▼
                  ┌───────────┐
                  │  已覆盖   │  covered_at 写入，等待当日测验
                  └─────┬─────┘
       当日测验完成 │ 或 次日补记(FR-014)
                        ▼
                  ┌───────────┐
                  │  已完成   │  completed_at 写入 → 已完成轮数 +1
                  └─────┬─────┘
            下一次分配当日集合
                        ▼
              新建 round_no = N+1（游标归位到词库首个单词）
```

不变量（Invariants）：

1. 同一账号至多一行 `completed_at IS NULL`。
2. `completed_at` 非空 ⇒ `covered_at` 非空。
3. 一轮内，`cursor_word_id` 单调不减；跨轮时重置为词库最小 `Word.id`。
4. 一轮内分配给某账号的单词 id 集合互不重复（由游标单调推进保证）。
5. 单日集合**不跨轮**：当前轮剩余不足每日目标时，只分配剩余部分（`FR-009`）。

## 与既有实体的关系（只读复用，不改语义）

| 既有实体 | 关系 | 本功能如何使用 |
|---|---|---|
| `words` | 词库 | 按 `id` 升序作为轮内顺序；`max(id)` 判定覆盖完成 |
| `daily_sets` / `daily_set_items` | 每日集合与浏览标记 | 仍然逐日生成与标记；轮次只决定"取哪些词"，不改动其结构 |
| `quiz_attempts`（`kind='daily'`） | 今日测验 | 其 `finished_at` 作为"当日测验完成"信号，驱动轮次 → 已完成 |
| `wrong_words` / `wrong_word_archive` | 错题本 / 错题库 | **不受轮次影响**：跨轮不清空、不改动 |
| `settings`（每日目标） | 每日目标 | 仍决定当日分配上限；规则不变 |

## 迁移（`004_study_rounds`）

1. 建 `study_rounds` 表与索引（含部分唯一索引）。
2. **不回填历史账号**（范围排除，见 research R-005）：迁移不读取 `daily_set_items`，不为任何已有账号预建轮次行；已有学习历史的账号升级后的行为不在本版定义范围。
3. 新增账号 / 无学习记录的账号：首次访问学习页或首页时惰性创建 `round_no = 1`（`cursor_word_id = MIN(words.id)`）。

## 验证要点

- 一轮结束时，该轮分配的单词 id 集合 = 词库全部单词 id（各一次）。
- 跨轮后，`wrong_words` / `wrong_word_archive` / 历史 `daily_set_items` 行数与内容不变（`FR-008`）。
- 同一账号并发 / 多设备请求下，不出现两个"进行中"轮次（依赖部分唯一索引 + 单写入口）。
