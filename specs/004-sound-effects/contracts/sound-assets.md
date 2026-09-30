# Contract: 音源资产（Sound Assets）

**Version**: 1 | **Date**: 2026-09-30 | **Spec**: [../spec.md](../spec.md)

## 1. 契约范围

音源是**构建期产物**：由脚本用项目已有的 TTS 引擎合成后落盘，运行时只按路径加载播放，不做任何网络合成。本契约约束音源的**目录、命名、格式、参数与清单文件**，供生成脚本、前端播放与契约测试三方对齐。

## 2. 目录与命名

| 项 | 值 |
|---|---|
| 源目录 | `frontend/public/sounds/`（构建时原样复制到 `dist/sounds/`） |
| 运行时路径 | `${import.meta.env.BASE_URL}sounds/<file>`（同域静态资源，**不向第三方请求**，FR-022） |
| 文件格式 | MP3（`audio/mpeg`），单声道即可 |
| 命名规则 | 小写下划线，与事件标识一一对应（见下表） |

## 3. 事件 ↔ 文件（共 18 条，唯一事实来源）

| 事件标识 | 台词（送入 TTS 的文本） | 文件 |
|---|---|---|
| `page.home` | Stick together, team. | `page_home.mp3` |
| `page.study` | OK, let's go! | `page_study.mp3` |
| `page.quiz` | Fire in the hole! | `page_quiz.mp3` |
| `page.wrong` | Bombs on the ground here. | `page_wrong.mp3` |
| `page.summary` | Keep going and stay strong, team. | `page_summary.mp3` |
| `quiz.start` | Come get some! | `quiz_start.mp3` |
| `streak.1` | First blood | `streak_1.mp3` |
| `streak.2` | Double kill | `streak_2.mp3` |
| `streak.3` | Triple kill | `streak_3.mp3` |
| `streak.4` | Quadra kill | `streak_4.mp3` |
| `streak.5` | Penta kill | `streak_5.mp3` |
| `streak.6` | Hexa kill | `streak_6.mp3` |
| `streak.7` | Hepta kill | `streak_7.mp3` |
| `streak.8` | Octa kill | `streak_8.mp3` |
| `streak.9` | Nona kill | `streak_9.mp3` |
| `streak.10` | Deca kill | `streak_10.mp3` |
| `streak.extend` | Good job | `streak_extend.mp3` |
| `answer.wrong` | Storm the front. | `answer_wrong.mp3` |

不在上表中的任何交互**不得发声**（FR-011）。

## 4. 生成参数（默认，可命令行覆盖）

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--voice` | `en-US-GuyNeural` | 男声，激情播报风格 |
| `--rate` | `+15%` | 语速偏快，体现"高昂激情"（FR-021） |
| `--pitch` | `+8Hz` | 音高上扬 |
| `--out-dir` | `frontend/public/sounds` | 输出目录 |

生成脚本：`backend/scripts/generate_sound_assets.py`（**仅开发期使用，不进镜像**；音源产物进构建产物）。

## 5. 质量约束

| 约束 | 阈值 | 依据 |
|---|---|---|
| 单条时长 | ≤ 2500 ms | FR-021（改用自备真人音源后放宽，实测最长 2324 ms） |
| 单条体积 | ≤ 30 KB | R-012 预算 |
| 18 条总体积 | ≤ 400 KB（实测 363.7 KB） | SC-009 |
| 首屏加载 | 音效关闭时不加载任何音源文件；`preload='none'` | SC-008 / SC-009 |
| 外部请求 | 0 | SC-010 / FR-022 |

## 6. 清单文件 `manifest.json`（由脚本产出）

```json
{
  "version": 1,
  "generated_at": "2026-09-30T10:40:00+08:00",
  "voice": "en-US-GuyNeural",
  "rate": "+15%",
  "pitch": "+8Hz",
  "entries": [
    { "event": "page.home", "file": "page_home.mp3", "text": "Stick together, team.", "duration_ms": 1450, "bytes": 12980 }
  ]
}
```

## 7. 契约测试要求

测试必须校验（自动化，见 `quickstart.md`）：

1. `manifest.json` 的 `entries` 覆盖第 3 节全部 18 个事件，**无缺失、无多余**
2. 每个 `file` 在 `frontend/public/sounds/` 下存在且非空
3. 每条 `duration_ms ≤ 2000`、`bytes ≤ 30720`
4. 前端事件映射表与 `manifest.json` 的事件集合**完全一致**（防止改了配置忘了生成，或反之）

## 8. 变更规则

- 只改**台词文本**：改映射表 + 重新跑生成脚本，`file` 名保持不变（FR-028：不影响触发逻辑）
- 增删事件：同步改本契约、映射表、脚本与契约测试（constitution II 契约先行）
- 改音色/语速：改脚本默认参数 → 重新生成全部音源 → 更新 `manifest.json` 中的 `voice/rate/pitch`
