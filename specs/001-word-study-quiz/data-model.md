# Data Model: 中考英语单词学习测验与错题本

**Feature**: 001-word-study-quiz | **Date**: 2026-09-28 | **Storage**: SQLite（WAL）

## Entities

### users — 注册用户（学生）

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| login_name | VARCHAR(32) | NOT NULL（登录名原文，3–20 位字母 / 数字 / 下划线） |
| login_name_norm | VARCHAR(32) | NOT NULL, UNIQUE（登录名小写归一值，用于重名判断与登录匹配） |
| nickname | VARCHAR(64) | NOT NULL（用户名昵称，1–24 字符，**允许重复**） |
| password_hash | VARCHAR(255) | NOT NULL（bcrypt，永不返回给客户端） |
| created_at | DATETIME | NOT NULL（UTC） |

**Indexes**: `UNIQUE(login_name_norm)`（大小写不敏感去重）

**Rules**: 登录名不做邮箱校验；`login_name_norm = lower(login_name)`，注册与登录均以该值匹配（FR-001/FR-002/FR-003）；昵称仅展示、允许重复，不参与任何唯一性判断；任何响应/日志不得包含 `password_hash` 或明文口令（FR-005）。

### user_settings — 用户配置

| Field | Type | Constraints |
|---|---|---|
| user_id | INTEGER | PK, FK → users.id ON DELETE CASCADE |
| daily_goal | INTEGER | NOT NULL, DEFAULT 20, CHECK(daily_goal BETWEEN 1 AND 200) |
| updated_at | DATETIME | NOT NULL |

**Rules**: 用户注册时创建默认行（`daily_goal=20`）；变更当日不影响已生成的当日集合（FR-010）。

### words — 词库（内置种子）

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| spelling | VARCHAR(64) | NOT NULL, UNIQUE（英文单词） |
| meaning_zh | VARCHAR(255) | NOT NULL（中文释义） |
| phrase | VARCHAR(255) | NULL（常用短语） |
| phonetic | VARCHAR(64) | NULL（音标，可选） |
| created_at | DATETIME | NOT NULL |

**Rules**: 由 Alembic 迁移从 `seeds/words.txt`（统一格式 `单词 词性.释义 | 短语1；短语2`）导入，按 `spelling` 幂等 upsert；替换词表不得删除该表已有行以外的用户数据（FR-011）。分配顺序按 `id` 升序（稳定、可预期）。

### daily_sets — 每日学习任务

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | NOT NULL, FK → users.id ON DELETE CASCADE |
| study_date | DATE | NOT NULL（服务端 UTC+8 计算的日期） |
| created_at | DATETIME | NOT NULL |

**Indexes**: `UNIQUE(user_id, study_date)`（天然幂等，防止重复生成）

### daily_set_items — 当日单词明细与浏览状态

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| daily_set_id | INTEGER | NOT NULL, FK → daily_sets.id ON DELETE CASCADE |
| word_id | INTEGER | NOT NULL, FK → words.id |
| order_index | INTEGER | NOT NULL（展示顺序） |
| viewed_at | DATETIME | NULL（NULL = 未浏览） |

**Indexes**: `UNIQUE(daily_set_id, word_id)`; `INDEX(daily_set_id, order_index)`

**Rules**: 数量 = `min(daily_goal, 未学习单词数)`；某一单词一旦出现在任意 `daily_set_items` 中即视为"已学习"，不再进入后续每日分配（Assumptions）；标记浏览幂等，重复提交保留首次 `viewed_at`。

### quiz_attempts — 一次测验 / 练习

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | NOT NULL, FK → users.id ON DELETE CASCADE |
| kind | VARCHAR(16) | NOT NULL, CHECK(kind IN ('daily','review')) |
| study_date | DATE | NULL（kind='daily' 时有值） |
| started_at | DATETIME | NOT NULL |
| finished_at | DATETIME | NULL（NULL = 进行中） |
| total_count | INTEGER | NOT NULL, DEFAULT 0 |
| correct_count | INTEGER | NOT NULL, DEFAULT 0 |
| wrong_count | INTEGER | NOT NULL, DEFAULT 0 |

### quiz_answers — 作答明细（支撑结果报告）

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| attempt_id | INTEGER | NOT NULL, FK → quiz_attempts.id ON DELETE CASCADE |
| word_id | INTEGER | NOT NULL, FK → words.id |
| question_type | VARCHAR(8) | NOT NULL, CHECK(question_type IN ('en2zh','zh2en')) |
| choice_index | INTEGER | NOT NULL（0–3） |
| is_correct | BOOLEAN | NOT NULL |
| answered_at | DATETIME | NOT NULL |

**Indexes**: `UNIQUE(attempt_id, word_id)`（同一轮中每词一题，重复提交以最后一次为准）

### wrong_words — 错题本（核心约束载体）

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | NOT NULL, FK → users.id ON DELETE CASCADE |
| word_id | INTEGER | NOT NULL, FK → words.id ON DELETE CASCADE |
| added_at | DATETIME | NOT NULL（**首次**答错时间） |

**Indexes**: `UNIQUE(user_id, word_id)`（同一单词仅一条记录，FR-030）; `INDEX(user_id, added_at)`

---

## Relationships

```text
users 1──1 user_settings
users 1──N daily_sets 1──N daily_set_items N──1 words
users 1──N quiz_attempts 1──N quiz_answers N──1 words
users 1──N wrong_words N──1 words
```

「单词是否已学习」不建独立表：由该用户是否已有对应 `daily_set_items` 记录判定（YAGNI）。

## State Transitions

### 当日学习与测验解锁

```text
[未生成] --首次访问学习页--> daily_sets(已生成, items.viewed_at=NULL)
items: 未浏览 (viewed_at NULL) --标记已浏览--> 已浏览 (viewed_at=时间戳, 不可逆)
全部 items 已浏览 --> 测验解锁 (quiz_unlocked = true)
存在任一未浏览 --> 测验锁定：start 返回 409 quiz_locked，入口前端置灰
```

`quiz_unlocked` **不落库**，由 `viewed_count == total_count` 实时计算，避免冗余状态与不一致（FR-018/FR-019）。

### 错题本生命周期（唯一移除路径）

```text
[不存在] --今日测验答错--> 存在 (added_at=now)
存在 --今日测验答对--> 存在（无任何写操作，FR-026）
存在 --专项练习答错--> 存在（added_at 不变，FR-037）
存在 --专项练习答对--> 已删除（唯一移除路径，FR-038）
存在 --日期切换 / 重新登录 / 学新词 / 改设置--> 存在（无删除语句，FR-031）
```

### 测验 / 练习轮次

```text
attempt: started (finished_at NULL) --最后一题提交--> finished (finished_at, 报告数据)
```

## Validation Rules

| 对象 | 规则 | 来源 |
|---|---|---|
| login_name | 3–20 位，仅字母 / 数字 / 下划线，不含中文与空格；按小写归一后全局唯一 | FR-001 / FR-002 |
| nickname | 1–24 字符，必填，允许重复（仅展示） | FR-001 |
| password | ≥ 6 位，不限制字符组合；仅存 bcrypt 哈希 | FR-001 / FR-005 |
| daily_goal | 整数 1–200，默认 20 | FR-007 / FR-009 |
| 当日集合 | 数量 = min(daily_goal, 未学习单词数)；当日稳定 | FR-010 / FR-014 / FR-020 |
| 浏览标记 | 仅当日集合内的 word_id 可标记，否则 404 `word_not_in_today_set` | FR-017 |
| 测验开启 | 需 `viewed_count == total_count`，否则 409 `quiz_locked` | FR-018 / FR-019 |
| 题目选项 | 恰好 4 项、1 项正确、干扰项来自词库其他单词且文本去重 | FR-024 / Edge Cases |
| 错题唯一性 | `(user_id, word_id)` 唯一；重复答错不新增、不改 `added_at` | FR-030 |
| 错题删除 | 仅 `kind='review'` 且答对的路径允许 DELETE | FR-031 / FR-038 |
| 发音 | 代理超时 2s；失败返回 `pronunciation_unavailable`，前端降级 | FR-016 / SC-006 |
