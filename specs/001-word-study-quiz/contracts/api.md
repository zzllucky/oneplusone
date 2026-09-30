# API Contract: 中考英语单词学习测验与错题本

**Feature**: 001-word-study-quiz | **Date**: 2026-09-28 | **Base**: `/api`

所有请求/响应为 `application/json`（`GET /api/pronounce/{word}` 除外，返回音频字节）。
认证：`Authorization: Bearer <access_token>`（JWT，有效期 7 天）。除注册、登录外全部接口需认证，缺失或失效返回 `401 unauthorized`。

统一错误响应：

```json
{ "error": { "code": "quiz_locked", "message": "请先完成今日全部单词浏览" } }
```

**Error codes**: `invalid_credentials` · `login_name_taken` · `weak_password` · `invalid_login_name` · `invalid_nickname` · `unauthorized` · `goal_out_of_range` · `word_not_in_today_set` · `quiz_locked` · `no_wrong_words` · `attempt_not_found` · `question_not_found` · `attempt_already_finished` · `pronunciation_unavailable`

---

## Auth

### POST /api/auth/register

Request: `{ "login_name": "stu01", "nickname": "小明", "password": "abc123" }`
Response `201`: `{ "user": { "id": 1, "login_name": "stu01", "nickname": "小明" }, "access_token": "string", "token_type": "bearer" }`
Errors: `422 invalid_login_name`（非 3–20 位字母/数字/下划线） / `422 invalid_nickname`（空或超 24 字符） / `422 weak_password`（< 6 位） / `409 login_name_taken`（含仅大小写不同的重名）
Rules: 不收集、不校验邮箱；`login_name` 按小写归一去重；昵称允许重复；密码 ≥ 6 位且不限制字符组合；注册即登录（FR-001 / FR-002）。

### POST /api/auth/login

Request: `{ "login_name": "stu01", "password": "abc123" }`
Response `200`: `{ "access_token": "string", "token_type": "bearer", "user": { "id": 1, "login_name": "stu01", "nickname": "小明" } }`
Errors: `401 invalid_credentials`（不区分登录名不存在与密码错误，FR-003）
Rules: 登录名按小写归一匹配（`Stu01` 与 `stu01` 等价，FR-003）。

### GET /api/auth/me

Response `200`: `{ "id": 1, "login_name": "stu01", "nickname": "小明", "daily_goal": 20 }`

---

## Settings

### GET /api/settings

Response `200`: `{ "daily_goal": 20, "updated_at": "2026-09-28T10:00:00Z" }`

### PUT /api/settings

Request: `{ "daily_goal": 30 }`
Response `200`: `{ "daily_goal": 30, "updated_at": "..." }`
Errors: `422 goal_out_of_range`（1–200）
Note: 当日已生成的集合不受影响，次日生效（FR-010）。

---

## Home

### GET /api/home/summary

Response `200`:

```json
{
  "user": { "id": 1, "login_name": "stu01", "nickname": "小明" },
  "daily_goal": 20,
  "today": {
    "study_date": "2026-09-28",
    "total_count": 20,
    "viewed_count": 6,
    "all_viewed": false,
    "quiz_unlocked": false
  },
  "wrong_word_count": 12
}
```

（FR-041 / FR-032）

---

## Study

### GET /api/study/today

首次访问即按 `daily_goal` 生成当日集合（未学单词，`words.id` 升序），当日重复访问返回同一集合。
Response `200`:

```json
{
  "study_date": "2026-09-28",
  "total_count": 20,
  "viewed_count": 0,
  "all_viewed": false,
  "quiz_unlocked": false,
  "library_exhausted": false,
  "items": [
    { "word_id": 101, "spelling": "ability", "meaning_zh": "能力；才能",
      "phrase": "the ability to do sth", "phonetic": "/əˈbɪləti/",
      "order_index": 1, "viewed_at": null }
  ]
}
```

`library_exhausted=true` 表示未学单词不足目标数（FR-020）。

### POST /api/study/today/items/{word_id}/view

Response `200`: `{ "word_id": 101, "viewed_count": 7, "total_count": 20, "all_viewed": false, "quiz_unlocked": false }`
Errors: `404 word_not_in_today_set`
Rules: 幂等，重复提交保留首次 `viewed_at`（FR-017）。

### GET /api/pronounce/{word}

Response `200`: `audio/mpeg`（服务端代理第三方发音接口，带磁盘缓存、2s 超时）
Errors: `404 pronunciation_unavailable` —— 前端收到即调用浏览器语音合成朗读（FR-016 / SC-006）

---

## Quiz — 今日测验

### POST /api/quiz/today/start

Request: `{}`
Response `200`:

```json
{
  "attempt_id": 55,
  "questions": [
    { "question_id": 901, "word_id": 101, "type": "en2zh",
      "prompt": "ability", "options": ["能力；才能", "机会", "建议", "习惯"] }
  ]
}
```

Rules: 题量 = 当日单词数，每词一题；题型随机 `en2zh` / `zh2en`；选项 4 项、1 项正确、干扰项来自词库其他单词且文本去重；**不下发正确答案**（提交后返回）；当日已有未完成的 attempt 则复用。
Errors: `409 quiz_locked`（存在未浏览单词，FR-018）

### POST /api/quiz/today/answer

Request: `{ "question_id": 901, "choice_index": 0 }`
Response `200`:

```json
{ "question_id": 901, "is_correct": false, "correct_index": 1,
  "added_to_wrong_words": true }
```

Rules: 答错 → 写入错题本（`added_at=now`，已存在则不新增、不改时间）；**答对 → `added_to_wrong_words=false` 且不执行任何删除**（FR-025 / FR-026 / FR-030）。

### POST /api/quiz/today/finish

Request: `{}`
Response `200`:

```json
{ "attempt_id": 55, "total_count": 20, "correct_count": 17, "wrong_count": 3,
  "accuracy": 0.85, "duration_seconds": 240,
  "new_wrong_words": [101, 233, 456] }
```

（FR-028）

---

## Wrong Words

### GET /api/wrong-words

Query: `page=1&page_size=20`
Response `200`:

```json
{ "total": 12, "page": 1, "page_size": 20,
  "items": [ { "word_id": 101, "spelling": "ability", "meaning_zh": "能力；才能",
               "phrase": "the ability to do sth", "phonetic": "/əˈbɪləti/",
               "added_at": "2026-09-27T09:15:00Z" } ] }
```

（FR-029 / FR-033）

---

## Quiz — 错题专项练习

### POST /api/quiz/review/start

Request: `{}`
Response `200`: 同今日测验结构（`attempt_id`, `questions[]`），题目**仅**来自当前错题本。
Errors: `409 no_wrong_words`（FR-033 / FR-035）

### POST /api/quiz/review/answer

Request: `{ "question_id": 902, "choice_index": 2 }`
Response `200`:

```json
{ "question_id": 902, "is_correct": true, "correct_index": 2,
  "removed_from_wrong_words": true }
```

Rules: 答错 → `removed_from_wrong_words=false`，错题保留且 `added_at` 不变（FR-037）；答对 → 删除该错题记录，这是**唯一**的删除路径（FR-038 / FR-031）。

### POST /api/quiz/review/finish

Request: `{}`
Response `200`:

```json
{ "attempt_id": 56, "total_count": 12, "correct_count": 9, "wrong_count": 3,
  "accuracy": 0.75, "duration_seconds": 180, "remaining_wrong_count": 3 }
```

（FR-039）

---

## Contract Test Coverage（tests/contract）

每个端点至少一条契约测试，校验：状态码、必填字段、字段类型、错误码一致性；并覆盖两条否定契约 —— 未完成浏览时 `POST /api/quiz/today/start` 返回 `409 quiz_locked`；今日测验答对后 `GET /api/wrong-words` 中该单词仍存在。
