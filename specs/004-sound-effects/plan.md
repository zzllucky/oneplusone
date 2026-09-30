# Implementation Plan: 学习音效反馈（Sound Effects）

**Branch**: `004-sound-effects` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-sound-effects/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

为单词学习站点增加"音效反馈"：按用户指定的 18 类事件播放**自产英文语音**（页面进入 5 句、开始测验 `Come get some!`、连对 1–10 的连杀台词、连对 >10 的 `Good job`、答错 `Storm the front.`），其余交互一律静音。

技术路径：**构建期**用项目已有的 TTS 引擎（edge-tts，`en-US-GuyNeural` +15% +8Hz）把 18 条短句预生成为 mp3，放到 `frontend/public/sounds/` 随构建产物发布；**运行时**用一个独立播放器单例按路径播放（后播覆盖先播、发音优先跳过、失败静默降级）；开关与音量存 `localStorage`（**默认关闭**）。**不新增后端接口、不改数据库、不引入新依赖、不产生任何外部请求。**

## Technical Context

**Language/Version**: TypeScript 5.6 / Vue 3.5（前端）；Python 3.12（仅音源生成脚本，复用既有 venv）

**Primary Dependencies**: Vue 3.5、Pinia 2、vue-router 4、Vitest 2 + jsdom + @vue/test-utils（均在用）；edge-tts（**已在用**，仅构建期）

**Storage**: 静态音源文件（mp3，随 `dist/sounds/`）+ `localStorage` 偏好；**无数据库变更**

**Testing**: Vitest（前端单元/契约，`npm test`）、`vue-tsc` 类型检查、`vite build` 构建校验 + 人工听感验收

**Target Platform**: 现代浏览器（Chrome / Edge / Safari，桌面与移动）；后端静态托管前端产物（Docker 或云服务器 venv+systemd 两种形态均适用）

**Project Type**: Web 应用（前端体验增强，零后端改动）

**Performance Goals**: 点击答案到出声 ≤150ms（SC-004）；首屏可交互时间增量 ≤1s（SC-009）；音源总计 ≤300KB

**Constraints**: 离线可用；0 外部网络请求；不采集任何行为数据；音效偏好不进账号；单条语音 ≤2 秒；默认关闭

**Scale/Scope**: 单用户设备级；18 个音源文件、1 个前端模块、1 个生成脚本、1 个设置页区块

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 条款 | 结论 | 依据 |
|---|---|---|
| I 库优先（自包含模块） | **PASS** | 新增 `frontend/src/sounds/`：`events.ts`（映射）+ `soundEffects.ts`（播放/计数/偏好），职责单一，自带单测与用途说明 |
| II 契约先行 | **PASS** | 先产出 `contracts/sound-assets.md`（18 条事件 ↔ 文件、格式、时长、manifest），再实现 |
| III 测试先行 | **PASS** | 任务按 TDD 排序：先写失败的 vitest 用例（映射、连对、偏好、播放行为），再实现 |
| IV 集成测试覆盖接缝 | **PASS** | 接缝为「路由进入 / 答题结果 → 音效模块」：组件级测试（@vue/test-utils）+ 资产契约测试覆盖；无跨服务通信 |
| V 可观测性 / 版本 / 简洁 | **PASS** | 播放失败 `console.warn` 并静默降级（前端无结构化日志体系，不引入）；版本号随 CHANGELOG 升到 0.3.0；零新增依赖 |
| 技术栈由 plan 决定 | **PASS** | spec 未出现任何技术名；选型全部记录在本文件与 research.md |
| 依赖引入需论证 | **PASS** | 前端零新增依赖；音源复用后端**已有** edge-tts（R-014） |
| 数据与安全基线 | **PASS** | 不新增用户数据、不落库；偏好仅本机 localStorage |
| 领域合规（未成年人） | **PASS** | 不新增任何收集字段（FR-018/FR-024）、无行为追踪与埋点（FR-023）、无第三方共享（FR-022） |

**Gate 结果：PASS（无违规）** —— 无需填写 Complexity Tracking。

## Project Structure

### Documentation (this feature)

```text
specs/004-sound-effects/
├── plan.md              # 本文件
├── research.md          # Phase 0：14 条实现决策（音源生成/放置/播放/优先级/存储/测试）
├── data-model.md        # Phase 1：事件映射、连对状态、偏好格式、音源清单
├── contracts/
│   └── sound-assets.md  # Phase 1：18 条音源契约（目录、命名、格式、参数、manifest）
├── quickstart.md        # Phase 1：生成 + 自动化 + 16 条人工验收场景
└── tasks.md             # Phase 2（/speckit.tasks 产出，本命令不创建）
```

### Source Code (repository root)

```text
backend/
└── scripts/
    └── generate_sound_assets.py     # 新增：音源生成脚本（仅开发期，不进镜像）

frontend/
├── public/
│   └── sounds/                      # 新增：18 个 mp3 + manifest.json（构建产物，进仓库）
├── src/
│   ├── sounds/                      # 新增：自包含音效模块
│   │   ├── events.ts                # 事件 ↔ 台词 ↔ 文件映射（替换台词只改这里）
│   │   └── soundEffects.ts          # 播放（覆盖/音量/发音优先）、连对计数、偏好读写
│   ├── composables/
│   │   └── useAudioWarmup.ts        # 修改：导出「是否正在发音」供音效让位判断
│   ├── router/
│   │   └── index.ts                 # 修改：进入白名单页面时触发页面语音
│   ├── pages/
│   │   ├── SettingsPage.vue         # 修改：新增音效开关 + 音量滑块
│   │   ├── TodayQuizPage.vue        # 修改：start / select 接入音效
│   │   ├── ReviewQuizPage.vue       # 修改：start / select 接入音效
│   │   └── ArchiveQuizPage.vue      # 修改：start / select 接入音效
└── tests/
    └── unit/
        ├── soundEvents.spec.ts      # 新增：映射与 manifest 一致性、资产契约
        ├── soundEffects.spec.ts     # 新增：连对计数与复位、播放覆盖、发音优先
        └── soundPreferences.spec.ts # 新增：默认关闭、持久化、非法值回退
```

**Structure Decision**：沿用既有 web 应用结构（frontend/backend 分离）。音效是纯前端能力，故只在 `frontend/` 下新增一个自包含模块与静态资源目录；音源生成脚本放 `backend/scripts/`（复用后端已有 edge-tts 与 venv，与既有造数脚本同目录同约定）。后端 `src/` 无任何改动。

## Complexity Tracking

> 无 Constitution 违规，本节无需填写。

## Phase 0 / Phase 1 产出

- **Phase 0** → [research.md](./research.md)：R-001 ~ R-014（含 edge-tts 实跑探测：`Fire in the hole!` = 10.9 KB，音色参数可用）
- **Phase 1** → [data-model.md](./data-model.md)、[contracts/sound-assets.md](./contracts/sound-assets.md)、[quickstart.md](./quickstart.md)

## 交付影响（部署与版本）

- 版本号：`0.2.0` → `0.3.0`（新增功能，向后兼容），CHANGELOG 在 `/speckit.implement` 阶段补 `[0.3.0]` 条目
- 部署：`frontend/dist/sounds/` 自动随既有打包命令（Docker 镜像与 `deploy.tgz` 均含 `frontend/dist`），**无需改 Dockerfile、docker-compose 与 README 部署命令**
