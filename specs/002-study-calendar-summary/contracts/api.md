# API Contract: 学习日历总结

**Feature**: `002-study-calendar-summary` | **Date**: 2026-09-30 | 基线：既有 001 契约风格

## 通用约定

- **前缀 / 鉴权**：路由挂 `/api`（`main.py` 统一），新增域前缀 `/summary`；全部端点需登录，使用既有 `Depends(get_current_user)`，未登录返回既有 `401 {"detail":{"code":"unauthorized",...}}`。
- **只读**：本域所有端点为 `GET`，**不写入、不修改任何数据**。
- **时区**：入参 `month` / `date` 均按服务端时区 `Asia/Shanghai` 解释；响应中的 `date` 为 `YYYY-MM-DD` 字符串。
- **兼容性与合规**：新增端点，**不改任何既有端点的字段**；响应只包含该账号本人的汇总数字（FR-016 / FR-018），不含任何在线时长或行为轨迹字段（在线时长已整体移除）。
- **参数错误**：`month` 非 `YYYY-MM` → `400 {"detail":{"code":"invalid_month"}}`；`date` 非 `YYYY-MM-DD` → `400 {"detail":{"code":"invalid_date"}}`。

---

## `GET /api/summary/month`

查询某月的日历着色、每日学习词数、月度总计与连续学习天数。

**Query**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `month` | string `YYYY-MM` | 否 | 缺省 = 当前月（服务端时区） |

**200 响应**

```json
{
  "month": "2026-09",
  "today": "2026-09-30",
  "days": [
    { "date": "2026-09-01", "level": "gray",  "shade": 0, "learned_count": 0 },
    { "date": "2026-09-02", "level": "light", "shade": 0, "learned_count": 0 },
    { "date": "2026-09-03", "level": "deep",  "shade": 2, "learned_count": 18 }
  ],
  "month_total": {
    "learned_words": 246,
    "quiz":           { "rounds": 12, "answered": 120, "correct": 102, "wrong": 18 },
    "review_practice": { "rounds": 5,  "answered": 50,  "correct": 44,  "wrong": 6 },
    "archive_practice": { "rounds": 2, "answered": 20,  "correct": 17,  "wrong": 3 },
    "active_days": 14
  },
  "streak_days": 5
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `month` | string | 所查月份 |
| `today` | string | 服务端当前日期（供前端标记"今天"） |
| `days[]` | array | 该月**每一天**（含无记录日），按日期升序；长度 = 该月天数（28/29/30/31） |
| `days[].level` | `gray` \\| `light` \\| `deep` | 三级着色（FR-002 / FR-019） |
| `days[].shade` | int 0–3 | 深绿分档：0 = 非深绿；1 = 1–9 词；2 = 10–29 词；3 = ≥30 词 |
| `days[].learned_count` | int | 当天浏览过的单词数（FR-006） |
| `month_total.*` | object | 月度汇总（FR-022），**不含在线时长** |
| `month_total.quiz.rounds` | int | 当月完成的今日测验次数 |
| `streak_days` | int | 连续学习天数（FR-023；当天未学则从最近一次连续段计，不为 0） |

---

## `GET /api/summary/day`

查询某一天的四项明细。

**Query**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `date` | string `YYYY-MM-DD` | 是 | 目标日期 |

**200 响应**

```json
{
  "date": "2026-09-03",
  "has_record": true,
  "learned_count": 18,
  "quiz":            { "completed": true, "rounds": 1, "answered": 10, "correct": 8, "wrong": 2 },
  "review_practice": { "rounds": 2, "answered": 20, "correct": 18, "wrong": 2 },
  "archive_practice": { "rounds": 0, "answered": 0, "correct": 0, "wrong": 0 }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `has_record` | bool | `false` = 当天无任何记录（灰色日、未来日期、注册前日期）→ 前端提示"当天没有学习记录"（US3） |
| `learned_count` | int | 当天浏览过的单词数（FR-006） |
| `quiz.completed` | bool | 当天是否完成过今日测验 |
| `quiz.rounds` / `answered` / `correct` / `wrong` | int | 今日测验结果（FR-008） |
| `review_practice.*` | int ×4 | 错题本专项练习：轮数 / 答题数 / 答对 / 答错（FR-009） |
| `archive_practice.*` | int ×4 | 错题库专项练习（FR-010） |

**无记录时**仍返回 `200`（**不返回 404**），除 `date` 外全为 `false` / `0`。

---

## 前端消费约定

| 位置 | 展示 | 来源 |
|---|---|---|
| 总结页月历 | 7 列网格（**周一为第一列**），每天一个色块 | `days[].level` + `days[].shade` |
| 今天 | 加可辨识边框 / 圆点标识 | `today` |
| 月度汇总面板 | 总学习词数、今日测验（答题 / 对 / 错）、错题本专项、错题库专项、有活动天数 | `month_total.*` |
| 连续天数 | 「连续学习 N 天」 | `streak_days` |
| 单日明细面板 | 学习单词数、今日测验对 / 错（含正确率）、错题本专项、错题库专项 | `GET /summary/day` |
| 灰色日 / 未来日 | 点击给出「当天没有学习记录」提示，**不显示空白面板** | `has_record=false` |
| 浅绿日 | 可点开，四项显示为 0 或"未进行" | `has_record=true` 且各项为 0 |

**兜底（两处）**：`month` / `date` 字段缺失、为 `null` 或接口异常时，日历区 / 明细区给出可理解的中文提示，**不出现空白块或英文错误堆栈**（spec Edge Cases）。

## 不变端点清单

`/api/auth/*`、`/api/settings/*`、`/api/home/*`、`/api/study/*`、`/api/quiz/*`、`/api/wrong-words/*`、`/api/pronounce/*` —— 字段名、类型、错误码与行为**全部不变**；本功能只新增 `/api/summary/*`。
