# API Contract: 词库循环学习与轮次统计

**Feature**: `003-library-cycle-rounds` | **Date**: 2026-09-29 | **Spec**: [spec.md](../spec.md)

契约变更范围：**只扩展既有 2 个端点的响应字段，不新增端点、不改错误码、不改既有字段语义**。
本文件是本次变更的唯一契约来源；实现、前端与测试均以此为准。

## 通用约定

- 认证：既有 `Authorization: Bearer <JWT>`；未登录 → `401`（既有行为不变）。
- 日期口径：服务端统一时区（Asia/Shanghai）的"当日"，与每日学习集合、今日测验一致。
- 兼容性：新增字段均为**附加**，既有字段的名称、类型、含义不变；旧客户端忽略新字段即可正常工作。
- 数据可见性（FR-011）：轮次与进度数据随既有账号鉴权返回，**仅本人可见**；本次变更不新增任何出站请求、第三方共享或跨账号可见路径。
- 轮末补记（FR-014）：补记在**轮次读取的统一入口**执行 —— `GET /home/summary` 与 `GET /study/today` 返回前都会先结算"已覆盖但覆盖日早于今天"的轮次，因此两个端点、刷新与跨设备请求返回的 `completed_rounds` 必然一致。

## 复用的既有端点（行为受本次变更影响，但签名不变）

| 方法 | 路径 | 本次变更带来的行为变化 |
|---|---|---|
| `POST` | `/quiz/daily/finish` | 提交今日测验时，若该日为本轮覆盖完成日，则轮次迁移为"已完成"（响应体不变） |
| `POST` | `/quiz/daily/start` | 词库耗尽后不再因"无词可学"而永久 `409 quiz_locked`；新一轮首日即可正常开始 |
| `GET` | `/study/today` | 词库耗尽后仍能返回新一轮的当日单词，不再返回空集合 |

错误码：本次**不新增**错误码；`quiz_locked`（未完成浏览）等既有错误码语义不变。

## 变更端点 1：`GET /home/summary`

**响应** `200`（新增两个字段，其余同既有）：

```json
{
  "user": { "id": 1, "login_name": "stu01", "nickname": "小明" },
  "daily_goal": 30,
  "today": {
    "study_date": "2026-09-29",
    "total_count": 30,
    "viewed_count": 12,
    "all_viewed": false,
    "quiz_unlocked": false
  },
  "wrong_word_count": 8,
  "archive_word_count": 15,
  "completed_rounds": 1,
  "current_round": {
    "round_no": 2,
    "learned_count": 120,
    "total_count": 2096,
    "pending_quiz": false
  }
}
```

新增字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `completed_rounds` | int | **已完成**的轮数；未完整学完一遍词库时为 `0`（FR-005） |
| `current_round` | object \| null | 当前进行中的轮次；无进行中轮次（理论上不出现）时为 `null` |
| `current_round.round_no` | int | 当前轮序号，从 `1` 开始 |
| `current_round.learned_count` | int | 本轮已学习（已进入当日集合）的单词数；**按本轮游标推算**，不受改每日目标影响 |
| `current_round.total_count` | int | 词库总数（用于展示"本轮已学 / 总数"） |
| `current_round.pending_quiz` | bool | 本轮最后一个单词已学完、但**当日测验尚未完成** → `true`（该轮暂不计入已完成）；其余情况为 `false`（FR-015） |

## 变更端点 2：`GET /study/today`

**响应** `200`（新增 `round` 字段，其余同既有）：

```json
{
  "study_date": "2026-09-29",
  "total_count": 30,
  "viewed_count": 12,
  "all_viewed": false,
  "quiz_unlocked": false,
  "library_exhausted": false,
  "round": {
    "round_no": 2,
    "learned_count": 120,
    "total_count": 2096,
    "pending_quiz": false
  },
  "items": [
    {
      "word_id": 121,
      "spelling": "ability",
      "meaning_zh": "n. 能力",
      "phrase": "have the ability to do；",
      "phonetic": "/əˈbɪləti/",
      "order_index": 1,
      "viewed_at": null
    }
  ]
}
```

新增字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `round` | object \| null | 当前轮次与进度（FR-006 / FR-013，供学习页展示） |
| `round.round_no` | int | 当前轮序号 |
| `round.learned_count` | int | 本轮已学单词数（含本次分配的单词） |
| `round.total_count` | int | 词库总数 |
| `round.pending_quiz` | bool | 同 `current_round.pending_quiz`：本轮已学完但当日测验未完成时 `true`（FR-015，供学习页提示） |

`library_exhausted` 语义调整：由"词库被学完（无词可分配）"改为**仅表示"当前轮剩余不足每日目标，本日按剩余数量分配"**；真正的"无词可学"状态在新一轮机制下不再出现。

## 不变端点（显式声明不受影响）

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/study/today/items/{word_id}/view` | 浏览标记与解锁规则不变 |
| `GET` / `POST` | `/wrong-words/*` | 错题本 / 错题库规则不变，跨轮不清空（FR-008） |
| `GET` / `POST` | `/quiz/review/*`、`/quiz/archive/*` | 专项练习规则不变 |
| `GET` / `POST` | `/settings/*` | 每日目标规则不变 |

## 前端展示约定（契约消费方）

| 位置 | 展示内容 | 来源字段 |
|---|---|---|
| 首页新卡片 | 「已完成 N 轮 · 当前第 M 轮」（`completed_rounds` 为 `0` 时显示"已完成 0 轮 · 当前第 1 轮"） | `completed_rounds`、`current_round.round_no` |
| 首页 | 大字体建议文案："建议初中会考前每天坚持学习，至少完成 10 轮"（固定文案，本版不随轮数改变；字号 **≥ 正文 1.5 倍 / Tailwind `text-lg` 及以上**） | 静态文案 |
| 首页 / 学习页 | 当 `pending_quiz = true`：**提示"本轮单词已学完，完成今日测验即可计入第 N 轮"**；为 `false` 时不显示 | `current_round.pending_quiz` / `round.pending_quiz` + `round_no` |
| 学习页进度区 | 「第 N 轮 · 本轮已学 X / Y」 | `round.round_no`、`round.learned_count`、`round.total_count` |
| 兜底（两处页面） | 轮次字段缺失 / 为 `null` / 接口异常时**不渲染轮次区**，页面其余部分照常显示，不出现空白块或英文错误堆栈 | — |
