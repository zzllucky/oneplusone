# Data Model: 初中英语语法学习（大纲 · 学卡 · 练习）

**Feature**: 006-grammar-study | **Date**: 2026-10-19 | **Storage**: SQLite（WAL），与单词模块同库

数据分两层：**内容层**（随系统发布，迁移 006 已落地）与**学习记录层**（用户产生，迁移 007 新增）。两层通过 `grammar_points.id`（字符串主键）关联，学习记录层不修改内容层任何字段。

---

## 一、内容层（已存在，迁移 006）

### grammar_points — 语法知识点（一张学习卡）

| Field | Type | Constraints |
|---|---|---|
| id | VARCHAR(16) | PK，形如 `G-A01`（合并卡以主知识点命名） |
| module | VARCHAR(2) | NOT NULL, INDEX，模块码（T/V/F/N/R/U/B/A/D/O/S/C …） |
| module_name | VARCHAR(32) | NOT NULL，如"形容词" |
| title | VARCHAR(64) | NOT NULL，如"比较级最高级构成" |
| depth | VARCHAR(8) | NOT NULL, CHECK(depth IN ('核心','了解')) |
| card_type | VARCHAR(16) | NOT NULL, CHECK(card_type IN ('rule','contrast','memorize')) |
| order_index | INTEGER | NOT NULL, DEFAULT 0，大纲展示顺序（先模块后编号） |
| payload | JSON | NOT NULL, DEFAULT {}，教研内容：`guess` / `rule`｜`contrast`｜`memorize` / `guess_callback` |
| covers | JSON | NOT NULL, DEFAULT []，覆盖的大纲知识点 id（普通卡 = [自身]，合并卡为多个） |
| created_at | DATETIME | NOT NULL（UTC） |

**Rules**: 82 张卡覆盖 85 个大纲知识点；大纲页以本表为准（R-008）；`payload` 是整块 JSON，前端按 `card_type` 选择渲染分支。

**payload 三种形态**（种子结构，仅供渲染参考）：

- `rule`：`rule`（一句话规则）、`signals`[]（信号词）、`formula`（变化公式）、`anchors`[{en,zh,note}]（锚例句）、`trap`{wrong,right,why}（陷阱对照）
- `contrast`：对比表形态（同 `rule` 的位置存放对比内容）
- `memorize`：记忆口诀形态

`guess` 为通用首段：`examples`[{en,zh}]、`question`、`options`[{key,text,feedback}]、`answer`（键）。

---

### grammar_questions — 语法题（卡内检测 + 题库练习共用）

| Field | Type | Constraints |
|---|---|---|
| id | VARCHAR(32) | PK，卡内 `G-A01-Q01`；题库 `G-A01-L1-01` |
| point_id | VARCHAR(16) | NOT NULL, FK → grammar_points.id ON DELETE CASCADE, INDEX |
| source | VARCHAR(8) | NOT NULL, CHECK(source IN ('card','bank')) |
| level | VARCHAR(2) | NOT NULL, CHECK(level IN ('L1','L2','L3')) |
| stem | TEXT | NOT NULL，题干 |
| explanation | TEXT | NOT NULL，解析（判分后返回） |
| error_tag | VARCHAR(16) | NULL，答错回链的知识点 id（种子中 = point_id） |
| order_index | INTEGER | NOT NULL, DEFAULT 0，层级内顺序 |
| created_at | DATETIME | NOT NULL |

**Rules**: 取题按 `level`（L1→L2→L3）+ `order_index` 递增，不洗牌（R-005）；每个知识点题库固定 6 题（L1/L2/L3 各 2 题），卡内检测 3 题。

---

### grammar_options — 题目选项

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| question_id | VARCHAR(32) | NOT NULL, FK → grammar_questions.id ON DELETE CASCADE, INDEX |
| key | VARCHAR(2) | NOT NULL，A / B / C / D |
| text | TEXT | NOT NULL |
| is_correct | BOOLEAN | NOT NULL, DEFAULT FALSE |
| feedback | TEXT | NULL，错项的错误原因说明 |
| order_index | INTEGER | NOT NULL, DEFAULT 0 |

**Rules**: 一题内正确项唯一；`is_correct` / `feedback` 在作答前不下发（R-006）。

---

## 二、学习记录层（新增，迁移 007）

### grammar_point_progress — 知识点掌握进度

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| user_id | INTEGER | NOT NULL, FK → users.id ON DELETE CASCADE |
| point_id | VARCHAR(16) | NOT NULL, FK → grammar_points.id ON DELETE CASCADE |
| status | VARCHAR(12) | NOT NULL, DEFAULT 'not_started', CHECK(status IN ('not_started','learning','mastered')) |
| check_total | INTEGER | NOT NULL, DEFAULT 0，学后检测累计作答数 |
| check_correct | INTEGER | NOT NULL, DEFAULT 0，学后检测累计答对数 |
| studied_at | DATETIME | NULL，首次打开学卡时间 |
| mastered_at | DATETIME | NULL，首次达成掌握时间 |
| updated_at | DATETIME | NOT NULL |

**Indexes**: `UNIQUE(user_id, point_id)`（一名学生一个知识点一条）、`INDEX(user_id, status)`（大纲页聚合计数）

**Rules**: 状态只由学后检测推进（R-002）：打开学卡 → `learning`；学后检测全对 → `mastered` + `mastered_at`；练习结果不修改本表。大纲页的"已掌握 / 全部"计数直接基于本表统计。

---

### grammar_attempts — 轮次（学后检测 / 题库练习）

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| user_id | INTEGER | NOT NULL, FK → users.id ON DELETE CASCADE |
| point_id | VARCHAR(16) | NOT NULL, FK → grammar_points.id ON DELETE CASCADE |
| source | VARCHAR(8) | NOT NULL, CHECK(source IN ('card','bank')) |
| level | VARCHAR(2) | NULL，题库练习的难度过滤（NULL = 全部层级），CHECK(level IS NULL OR level IN ('L1','L2','L3')) |
| total_count | INTEGER | NOT NULL, DEFAULT 0 |
| correct_count | INTEGER | NOT NULL, DEFAULT 0 |
| wrong_count | INTEGER | NOT NULL, DEFAULT 0 |
| started_at | DATETIME | NOT NULL |
| finished_at | DATETIME | NULL，非空即该轮已结束 |

**Indexes**: `INDEX(user_id, point_id)`、`INDEX(user_id, started_at)`

**Rules**: `finished_at IS NULL` 表示进行中；已结束轮次拒绝再次作答与再次结算（FR-016）；`source='card'` 的轮次在结算时判定掌握（R-002）。

---

### grammar_answers — 作答记录

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| attempt_id | INTEGER | NOT NULL, FK → grammar_attempts.id ON DELETE CASCADE |
| question_id | VARCHAR(32) | NOT NULL, FK → grammar_questions.id ON DELETE CASCADE |
| choice_key | VARCHAR(2) | NOT NULL，A / B / C / D |
| is_correct | BOOLEAN | NOT NULL |
| answered_at | DATETIME | NOT NULL |

**Indexes**: `UNIQUE(attempt_id, question_id)`（一轮内一题仅一条，重复提交以首次为准，FR-015）、`INDEX(question_id)`

**Rules**: 判分在 service 内一次事务完成：写入作答 → 更新轮次计数 → 按 `error_tag` 维护语法错题本 →（card 轮次结算时）更新掌握进度。

---

### grammar_wrong_points — 语法错题本

| Field | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| user_id | INTEGER | NOT NULL, FK → users.id ON DELETE CASCADE |
| point_id | VARCHAR(16) | NOT NULL, FK → grammar_points.id ON DELETE CASCADE |
| wrong_count | INTEGER | NOT NULL, DEFAULT 1，累计答错次数 |
| correct_streak | INTEGER | NOT NULL, DEFAULT 0，当前连续答对次数 |
| added_at | DATETIME | NOT NULL，首次进入错题本时间（后续答错不更新） |
| last_wrong_at | DATETIME | NOT NULL，最近一次答错时间 |

**Indexes**: `UNIQUE(user_id, point_id)`、`INDEX(user_id, added_at)`（列表按加入时间排序）

**Rules**: 与单词错题本同一套语义 —— 答错时不存在则插入（`wrong_count=1`、`correct_streak=0`），存在则 `wrong_count += 1`、`correct_streak = 0`、`last_wrong_at` 更新、`added_at` 保持不变；答对时 `correct_streak += 1`，达到阈值 `GRAMMAR_WRONG_REMOVE_STREAK = 2` 即删除该行（唯一移除路径，FR-013）。

---

## 三、状态流转

### 知识点掌握状态

```text
not_started ──(打开学卡 / 提交学后检测)──▶ learning
learning    ──(一次 card 轮次全部答对)───▶ mastered
mastered    ──(练习答错)─────────────────▶ mastered（不变，仅进错题本）
```

### 语法错题本

```text
(答错，error_tag 指向的知识点)
  ├─ 不存在该条目 → 插入（wrong_count=1, correct_streak=0）
  └─ 已存在       → wrong_count+1, correct_streak=0, last_wrong_at=now

(答对)
  └─ 已存在       → correct_streak+1；>= 2 → 删除条目（移出）
```

### 轮次

```text
start（source=card|bank）→ 进行中（finished_at IS NULL）
  → answer × N（逐题判分，唯一约束防重）
  → finish（回填 total/correct/wrong/accuracy/duration，card 轮次判定掌握）
  → 已结束（finished_at 非空，拒绝再作答 / 再结算）
```

---

## 四、规则常量（服务端集中定义）

| 常量 | 值 | 用途 |
|---|---|---|
| `GRAMMAR_WRONG_REMOVE_STREAK` | 2 | 语法错题本移除所需的连续答对次数（FR-013） |
| `GRAMMAR_LEVELS` | `('L1','L2','L3')` | 题库出题的层级递进顺序（FR-008） |
| `GRAMMAR_SOURCES` | `('card','bank')` | 轮次来源 |

---

## 五、与既有表的关系

- `users`：学习记录层四张表全部 `user_id → users.id ON DELETE CASCADE`，账号删除时一并清理（无孤儿数据）。
- `words` / `daily_sets` / `quiz_attempts` / `quiz_answers` / `wrong_words`：**无关联**，语法与单词两条链路互不影响（FR-020）。
- 迁移顺序：`006`（内容层，已执行）→ `007`（学习记录层，新增），`007` 不改动任何既有表。
