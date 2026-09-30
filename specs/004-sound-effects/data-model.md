# Data Model: 004-sound-effects（学习音效反馈）

**Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> 本功能**不新增任何数据库表/字段、不改后端接口**（FR-024）。数据只有三处：静态音源清单、会话内连对计数、设备本地偏好。

## 1. 音效事件与台词映射（Sound Event）— 静态配置

18 个事件，台词与音源一一对应（完整契约见 [contracts/sound-assets.md](./contracts/sound-assets.md)）：

| 事件标识 | 触发时机 | 台词 | 音源文件 |
|---|---|---|---|
| `page.home` | 进入首页 `/home` | Stick together, team. | `page_home.mp3` |
| `page.study` | 进入学习页 `/study` | OK, let's go! | `page_study.mp3` |
| `page.quiz` | 进入测验页 `/quiz` | Fire in the hole! | `page_quiz.mp3` |
| `page.wrong` | 进入错题页 `/wrong-words` | Bombs on the ground here. | `page_wrong.mp3` |
| `page.summary` | 进入总结页 `/summary` | Keep going and stay strong, team. | `page_summary.mp3` |
| `quiz.start` | 点击"开始测验" / "开始专项练习" | Come get some! | `quiz_start.mp3` |
| `streak.1` … `streak.10` | 连对第 N 题（1–10） | First blood / Double kill / Triple kill / Quadra kill / Penta kill / Hexa kill / Hepta kill / Octa kill / Nona kill / Deca kill | `streak_1.mp3` … `streak_10.mp3` |
| `streak.extend` | 连对第 11 题及以后每题 | Good job | `streak_extend.mp3` |
| `answer.wrong` | 答错任意一题 | Storm the front. | `answer_wrong.mp3` |

**明确不发声**（FR-011）：翻页、测验全部答完、轮次达成、进入 `/review` 与 `/archive`、导航切换、普通按钮、登录注册、保存设置。

## 2. 连对状态（Streak Counter）— 会话内内存态

| 字段 | 类型 | 说明 |
|---|---|---|
| `count` | int（≥0） | 当前连续答对题数 |
| `scope` | 会话内 | 仅存在于一次测验流程中，不持久化、不入库、不跨页面共享 |

状态转换：

```text
开始（点 start）        → count = 0
答对                    → count += 1
  count ≤ 10            → 播 streak.{count}
  count > 10            → 播 streak.extend
答错                    → 播 answer.wrong，count = 0
再次点击"开始"           → count = 0（FR-004）
刷新 / 换页面 / 重登录   → 计数丢失（视为新会话，count = 0）
```

## 3. 音效偏好（Sound Preference）— 设备本地持久化

存储位置：`localStorage['word-study-sound-prefs']`（**不进账号、不同步服务端**，FR-024）

| 字段 | 类型 | 默认值 | 校验规则 |
|---|---|---|---|
| `enabled` | boolean | **`false`**（FR-012 默认关闭） | 非 boolean 视为 `false` |
| `volume` | int（0–100，步进 10） | `70` | 越界或非数字回退为 `70`；0 视为静音但开关仍为开 |

读取规则：解析失败 / 字段缺失 / JSON 损坏 → 回退默认值（不抛错、不影响页面）；写入即时生效（无需"保存"按钮）。

## 4. 音源清单（Sound Manifest）— 构建产物

位置：`frontend/public/sounds/manifest.json`（由生成脚本产出，供契约测试与排查使用）

| 字段 | 类型 | 说明 |
|---|---|---|
| `version` | int | 清单格式版本（当前 `1`） |
| `voice` / `rate` / `pitch` | string | 生成时使用的 TTS 参数，便于复现 |
| `entries[]` | array | 每个事件一条：`event`、`file`、`text`、`duration_ms`、`bytes` |

约束：单条 `duration_ms ≤ 2000`（FR-021）、`bytes ≤ 30 KB`、`entries` 必须覆盖第 1 节的 18 个事件且无多余项。

## 5. 与既有数据模型的关系

- **无外键、无关联**：音效不读写任何学习数据
- **不触碰**：`users` / `daily_set*` / `quiz_*` / `study_rounds` / `wrong_words*`
- **唯一复用**：答题结果（`is_correct`）来自既有测验接口返回值，音效模块只消费它，不存储它（FR-023：不采集行为数据）
