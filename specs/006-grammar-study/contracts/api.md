# API Contract: 初中英语语法学习

**Feature**: 006-grammar-study | **Date**: 2026-10-19 | **Base**: `/api/grammar`

本文档是语法模块接口的**唯一契约来源**：后端实现、前端调用与契约测试均以本文件为准。

## 通用约定

- **认证**：全部端点需要登录态（`Authorization: Bearer <token>`）。缺失 / 失效 → `401 unauthorized`。
- **请求 / 响应**：`application/json`；字段名一律 snake_case。
- **错误模型**：`{"error": {"code": "...", "message": "..."}}`，`code` 为稳定标识，前端按 `code` 分支。
- **主键类型**：知识点与题目主键是**字符串**（`G-A01`、`G-A01-L1-01`），轮次主键是自增整数。
- **答案保护（FR-007，硬性）**：**作答之前**，任何响应**不得**包含正确选项、错因说明与对错判词。`payload` **不是原样下发**，服务端出库前必须经 `sanitize_payload()` 清洗（见下）。
- **幂等**：`view` 与同一轮次同一题的 `answer` 均幂等（FR-015）。
- **未完成轮次**：轮次一旦创建即独立存在。学生中途退出后再次发起**新建轮次**，不恢复、不复用上一轮未答题目，旧轮次保留为未完成（`finished_at IS NULL`）且永不自动结算（FR 边缘用例、US3-AC4）。

#### `sanitize_payload()` 清洗规则（服务端强制）

`grammar_points.payload` 是教研原始 JSON，含 `answer` 等答案字段，出库前必须递归清洗：

| 规则 | 处理 |
|---|---|
| `guess.answer` | **删除**（正解标识） |
| `guess.options[].feedback` | **删除**（文本含"对！/ 不对——"判词，等同于泄露正解） |
| `check[]` 内的题目 | 不出现在 `payload` 中（题目走 `grammar_questions` 表，见 §2 `check_questions`） |
| 其余键（examples / question / options[].key / options[].text / rule / contrast / memorize / signals / formula / anchors / trap / guess_callback 等） | 原样保留 |
| 递归兜底 | 任意层级出现键名 `answer`、`is_correct`、`correct_key` 一律删除，防止新增卡型漏网 |

> **为什么不能只删 `answer`**：种子卡 `G-A01` 的 `guess.options[*].feedback` 分别为"对！…"/"不对——…"，同时下发三个选项的反馈即可反推正解。因此反馈改为**选择之后**由 §3 端点按所选键单独返回。

### 错误码

| code | HTTP | 触发条件 |
|---|---|---|
| `unauthorized` | 401 | 未登录或令牌失效 |
| `grammar_point_not_found` | 404 | 知识点标识不存在 |
| `grammar_question_not_found` | 404 | 题目不存在（或不属于该轮次所属知识点） |
| `grammar_attempt_not_found` | 404 | 轮次不存在或不属于当前用户 |
| `grammar_attempt_already_finished` | 409 | 对已结束轮次作答 / 重复结算（FR-016） |
| `no_grammar_questions` | 409 | 该知识点无对应来源的题目（如无题库题却发起练习，FR-011） |
| `invalid_choice_key` | 422 | 提交的选项键不属于该题目（FR-017） |
| `validation_error` | 422 | 其余参数不合法（如 `level` 取值非法） |

> 上述 `grammar_*` 与 `no_grammar_questions` 需登记到后端 `errors.py` 的 `ERROR_MESSAGES`，否则 `message` 会退回 code 原文。

---

## 1. 获取语法大纲

`GET /api/grammar/outline`

按 `module` + `order_index` 分组返回全部知识点，附带当前用户的掌握状态与错题标记。

**Response 200**

```json
{
  "total_points": 82,
  "mastered_count": 3,
  "wrong_count": 1,
  "modules": [
    {
      "module": "A",
      "module_name": "形容词",
      "points": [
        {
          "id": "G-A01",
          "title": "比较级最高级构成",
          "depth": "核心",
          "card_type": "rule",
          "status": "mastered",
          "has_wrong": false,
          "question_count": 6
        }
      ]
    }
  ]
}
```

| Field | Type | 说明 |
|---|---|---|
| total_points | int | 知识点（学习卡）总数 |
| mastered_count | int | `status='mastered'` 的数量（FR-003） |
| wrong_count | int | 语法错题本中的知识点数（FR-003） |
| modules[].module / module_name | str | 模块码与模块名 |
| modules[].points[].id | str | 知识点标识 |
| modules[].points[].depth | str | `核心` / `了解` |
| modules[].points[].card_type | str | `rule` / `contrast` / `memorize` |
| modules[].points[].status | str | `not_started` / `learning` / `mastered` |
| modules[].points[].has_wrong | bool | 是否在语法错题本中（FR-002） |
| modules[].points[].question_count | int | 该知识点题库题数（`source='bank'`），为 0 时练习入口不可用 |

---

## 2. 获取知识点学卡

`GET /api/grammar/points/{point_id}`

返回学卡的教研内容与**卡内检测题的选项（不含答案）**。

**Response 200**

```json
{
  "point": {
    "id": "G-A01",
    "module": "A",
    "module_name": "形容词",
    "title": "比较级最高级构成",
    "depth": "核心",
    "card_type": "rule",
    "status": "not_started",
    "has_wrong": false
  },
  "payload": {
    "guess": {
      "examples": [{ "en": "Tom is taller than Jim.", "zh": "汤姆比吉姆高。" }],
      "question": "interesting 的比较级为什么是 more interesting？",
      "options": [
        { "key": "A", "text": "因为它是多音节词，比较级要在前面加 more，不能加 -er" },
        { "key": "B", "text": "因为它以 -ing 结尾" }
      ]
    },
    "rule": {
      "rule": "单音节和少数双音节词加 -er / -est；多音节词前加 more / most",
      "signals": ["-er", "-est", "more", "most"],
      "formula": "① 单音节：tall → taller → tallest …",
      "anchors": [{ "en": "Tom is taller than Jim.", "zh": "汤姆比吉姆高。", "note": "单音节加 -er" }],
      "trap": { "wrong": "…interestinger…", "right": "…more interesting…", "why": "多音节词不能加 -er" }
    },
    "guess_callback": "你刚才选的是 A——短词加 -er/-est，长词加 more/most。"
  },
  "check_questions": [
    {
      "question_id": "G-A01-Q01",
      "level": "L1",
      "stem": "Which is ____, the sun or the moon?",
      "options": [
        { "key": "A", "text": "big" },
        { "key": "B", "text": "bigger" },
        { "key": "C", "text": "biggest" },
        { "key": "D", "text": "the biggest" }
      ]
    }
  ]
}
```

**说明**

- `payload` 为 `sanitize_payload()` 清洗后的 JSON（见通用约定），`card_type` 决定前端渲染分支（`rule` / `contrast` / `memorize`）。
- `guess.options[]` **仅有 `key` 与 `text`**：无 `answer`、无 `feedback`。学生选择后的针对性反馈由 §2.1 端点按所选键返回（FR-004 + FR-007）。
- `check_questions` 仅含 `source='card'` 的题目与选项（`key` + `text`），不含正确答案（FR-007）。
- 404 `grammar_point_not_found`。

---

## 2.1 提交"猜一猜"并获取反馈

`POST /api/grammar/points/{point_id}/guess`

学生选择"猜一猜"选项后调用；服务端从**未清洗**的原始 `payload` 中取出所选选项的 `feedback` 返回。该反馈**在作答之后**才下发，因此不构成答案泄露（FR-007）。此环节不判分、不写库、不影响掌握状态。

**Request**

```json
{ "choice_key": "A" }
```

| Field | Type | Required | 说明 |
|---|---|---|---|
| choice_key | str | 是 | `payload.guess.options[].key` 之一（A–D） |

**Response 200**

```json
{ "point_id": "G-A01", "choice_key": "A", "feedback": "对！三个音节以上的词一律用 more / most，不能加 -er。" }
```

| Field | Type | 说明 |
|---|---|---|
| feedback | str | 所选选项的针对性解释；种子文本自带"对！/ 不对——"判词，属作答后反馈，允许下发 |

**错误**：404 `grammar_point_not_found`；422 `invalid_choice_key`（`choice_key` 不在该卡 `guess.options` 中）；401 `unauthorized`。

---

## 3. 标记已学（打开学卡）

`POST /api/grammar/points/{point_id}/view`

幂等：首次调用把进度置为 `learning` 并写入 `studied_at`；已是 `mastered` 时不降级。

**Response 200**

```json
{ "point_id": "G-A01", "status": "learning", "studied_at": "2026-10-19T10:00:00Z" }
```

404 `grammar_point_not_found`。

---

## 4. 开始学后检测

`POST /api/grammar/points/{point_id}/check/start`

建立 `source='card'` 的轮次，返回该知识点卡内检测题（按 `order_index`）。

**Request**: 空对象 `{}`（与既有 `POST /api/quiz/today/start` 一致）

**Response 200**

```json
{
  "attempt_id": 101,
  "source": "card",
  "point_id": "G-A01",
  "questions": [
    {
      "question_id": "G-A01-Q01",
      "level": "L1",
      "stem": "Which is ____, the sun or the moon?",
      "options": [{ "key": "A", "text": "big" }, { "key": "B", "text": "bigger" }]
    }
  ]
}
```

**错误**：404 `grammar_point_not_found`；409 `no_grammar_questions`（该知识点无卡内检测题）。

---

## 5. 开始题库练习

`POST /api/grammar/points/{point_id}/practice/start`

建立 `source='bank'` 的轮次，按 L1 → L2 → L3 顺序出题（R-005）。

**Request**

```json
{ "level": "L2" }
```

| Field | Type | Required | 说明 |
|---|---|---|---|
| level | str \| null | 否 | 只练某一层级（`L1`/`L2`/`L3`）；省略或 null = 全部层级 |

**Response 200**：结构同第 4 条，`source` 为 `bank`。

**错误**：404 `grammar_point_not_found`；409 `no_grammar_questions`（无题库题，FR-011）；422 `validation_error`（`level` 取值非法）。

---

## 6. 提交作答（学后检测与练习共用）

`POST /api/grammar/attempts/{attempt_id}/answer`

**Request**

```json
{ "question_id": "G-A01-Q01", "choice_key": "B" }
```

| Field | Type | Required | 说明 |
|---|---|---|---|
| question_id | str | 是 | 题目标识，必须属于该轮次所属知识点 |
| choice_key | str | 是 | 该题目选项键 A–D |

**Response 200**

```json
{
  "question_id": "G-A01-Q01",
  "is_correct": true,
  "correct_key": "B",
  "explanation": "两者比较 → bigger（重读闭音节双写 g）。",
  "feedback": null,
  "attempt": { "total_count": 3, "answered_count": 1, "correct_count": 1, "wrong_count": 0 },
  "added_to_wrong_points": false,
  "removed_from_wrong_points": false,
  "correct_streak": 1
}
```

| Field | Type | 说明 |
|---|---|---|
| is_correct | bool | 本题是否正确 |
| correct_key | str | 正确选项键（FR-009） |
| explanation | str | 题目解析 |
| feedback | str \| null | 所选错项的错因说明；答对时为 null（FR-005/FR-009） |
| attempt.total_count / answered_count / correct_count / wrong_count | int | 本轮进度 |
| added_to_wrong_points | bool | 答错时该知识点是否**新**进入语法错题本（FR-012） |
| removed_from_wrong_points | bool | 本次答对是否把该知识点移出语法错题本（FR-013） |
| correct_streak | int | 移出前 / 累加后的当前连续答对次数；不在错题本中为 0 |

**幂等与错误**

- 同一轮次同一题目重复提交：返回**首次**作答结果，不重复计分、不重复累加错题次数（FR-015）。
- 404 `grammar_attempt_not_found` / `grammar_question_not_found`；409 `grammar_attempt_already_finished`；422 `invalid_choice_key`（FR-017）。

---

## 7. 结算轮次

`POST /api/grammar/attempts/{attempt_id}/finish`

**Response 200**

```json
{
  "attempt_id": 101,
  "source": "card",
  "point_id": "G-A01",
  "total_count": 3,
  "correct_count": 3,
  "wrong_count": 0,
  "accuracy": 1.0,
  "duration_seconds": 42,
  "mastered": true,
  "status": "mastered"
}
```

| Field | Type | 说明 |
|---|---|---|
| accuracy | float | `round(correct / total, 4)`；`total=0` 时为 0 |
| duration_seconds | int | `started_at → finished_at` 秒数 |
| mastered | bool | 该轮是否达成掌握：仅 `source='card'` 且全部答对为真（FR-006） |
| status | str | 结算后该知识点的掌握状态（`not_started` / `learning` / `mastered`） |

**未答题目的处理**：结算**不要求**答完全部题目。未作答题不写 `grammar_answers`，既不计入 `correct_count` 也不计入 `wrong_count`；`total_count` 为本轮发出的题数，`accuracy = correct_count / total_count`，因此中途结算会拉低正确率（不视为答错）。

**错误**：404 `grammar_attempt_not_found`；409 `grammar_attempt_already_finished`（重复结算，FR-016）。

---

## 8. 语法错题本

`GET /api/grammar/wrong-points`

**Response 200**

```json
{
  "total": 1,
  "items": [
    {
      "point_id": "G-A01",
      "title": "比较级最高级构成",
      "module": "A",
      "module_name": "形容词",
      "wrong_count": 2,
      "correct_streak": 0,
      "added_at": "2026-10-19T10:05:00Z",
      "last_wrong_at": "2026-10-19T10:30:00Z"
    }
  ]
}
```

排序：按 `added_at` 升序、`id` 升序（与单词错题本一致）。前端点击条目跳转 `/grammar/{point_id}`（FR-014）。

---

## 契约测试要点（后端 `tests/contract/test_grammar_contract.py`）

端点共 9 个（含 §2.1）。

- 未登录访问 **9 个端点**一律 401 `unauthorized`（FR-018）。
- `GET /outline` 字段形状与 `mastered_count` / `wrong_count` 与实际数据一致。
- `GET /points/{id}` 的响应中**不得**出现 `is_correct`、`correct_key`、`explanation`、`feedback`、`answer`（答案保护，FR-007）：断言 `payload.guess` 无 `answer` 键、`payload.guess.options[*]` 仅含 `key`/`text`。
- `POST /points/{id}/guess` 覆盖：合法键返回 `feedback`、非法键 422 `invalid_choice_key`、未登录 401。
- `POST /check/start` / `POST /practice/start` 的响应中**不得**出现 `is_correct`、`correct_key`、`explanation`、`feedback`。
- `POST /practice/start` 对无题库题的知识点返回 409 `no_grammar_questions`。
- `POST /attempts/{id}/answer` 覆盖：正确、错误、重复提交幂等、非法选项键 422、已结束轮次 409。
- `POST /attempts/{id}/finish` 覆盖：全对掌握、未全对不掌握、重复结算 409、中途结算未答题不计入 wrong。
- 答错后 `GET /wrong-points` 出现该知识点；连续答对达标后消失。
- **账号隔离（FR-019）**：用户 A 的进度 / 轮次 / 错题本对用户 B 完全不可见（`GET /outline` 计数为 0、`GET /wrong-points` 为空、B 操作 A 的 `attempt_id` → 404 `grammar_attempt_not_found`）。
