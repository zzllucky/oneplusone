# Implementation Plan: 词库循环学习与轮次统计

**Branch**: `003-library-cycle-rounds` | **Date**: 2026-09-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-library-cycle-rounds/spec.md`

## Summary

词库（2096 词）被学完后，系统当前会进入"无词可分配"的卡死状态：学习页空、今日测验永久锁死。本功能让词库学完后**自动进入下一轮**（按词库原顺序从头再来，每轮每词恰好一次），并统计展示**已完成轮数**。

技术路径：在既有 FastAPI + SQLAlchemy 2.x + Alembic + SQLite 与 Vue 3 + Vite 栈上，**新增一张 `study_rounds` 表与一个 `round_service` 模块**，把"取词范围"从"排除全部历史已学词"改为"按当前轮游标取词"；轮次状态机 `进行中 → 已覆盖 → 已完成` 由"游标越界"与"当日测验完成"两个信号驱动；`GET /home/summary` 与 `GET /study/today` 各扩一个字段供首页与学习页展示。**不新增端点、不新增第三方依赖、不改动错题本 / 错题库规则**。

## Technical Context

**Language/Version**: Python 3.12（后端）；TypeScript 5.x + Node 20（前端构建）

**Primary Dependencies**: FastAPI 0.115+、SQLAlchemy 2.0+、Alembic 1.13+、Pydantic v2；Vue 3 + Vite 5 + vue-router 4 + Pinia 2 + Tailwind CSS 3（均为既有依赖，**本次不新增**）

**Storage**: SQLite 单文件（`data/app.db`，WAL）——新增 `study_rounds` 表；轮次由游标维护，不建单词—轮次归属表

**Testing**: pytest + FastAPI TestClient（unit / contract / integration 三层）；Vitest（前端组件，按需）

**Target Platform**: Linux 服务器 Docker 单容器（uvicorn）；客户端现代浏览器，视口 360 / 768 / 1440

**Project Type**: Web application（前后端分离，后端托管前端静态产物）

**Performance Goals**: 学习页与首页交互即时响应；每日分配为按主键升序的 `LIMIT` 查询（2096 词规模），接口 p95 < 300ms 与既有目标一致

**Constraints**: 单容器、无额外数据库服务；**一轮内每词恰好一次**且**单日集合不跨轮**；跨轮不得清空任何历史数据；新增字段不得涉及身份信息收集

**Scale/Scope**: 词库 2096 词；账号规模 < 1000，日活 < 200；改动面 = 1 张新表 + 1 个新服务模块 + 2 个端点扩字段 + 2 个前端页面 + 1 个迁移

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 章程条款 | 判定 | 落实方式 |
|---|---|---|
| I 库优先（模块自包含） | Pass | 新增 `round_service` 单一职责：轮次创建 / 游标推进 / 覆盖与完成判定 / 补记；`study_service` 只消费"本轮待分配词"，`quiz_service` 只发"当日测验完成"信号，模块间通过显式函数契约通信 |
| II 契约先行 | Pass | Phase 1 先产出 `contracts/api.md`（2 个端点的新增字段、不变端点清单、前端消费约定），实现与前端均以该文件为准 |
| III 测试先行 | Pass | 先写失败用例：① 词库耗尽后次日仍有词可学；② 完成当日测验后轮数 +1；③ 只浏览未测验不 +1；④ 跨轮不清错题本；再实现 |
| IV 集成测试覆盖关键接缝 | Pass | 用真实 SQLite + HTTP 链路跑"耗尽 → 新一轮 → 轮末测验 → 轮次完成 → 错题本不变"，禁止 mock 掩盖轮次与测验的接线 |
| V 可观测性 / 版本 / 简洁 | Pass | 轮次迁移与补记写结构化日志；**简洁**：采用游标方案而非单词—轮次归属表（YAGNI），不引入新依赖、不引入调度组件 |
| 附加约束：技术栈由 plan 决定 | Pass | 技术栈仅出现在本文件；spec.md 保持技术中立 |
| 附加约束：依赖需论证 | Pass | **本次零新增依赖**，既有栈已足够（见 research R-001/R-002） |
| 附加约束：数据与安全 | Pass | 轮次数据仅本人可见（随既有账号鉴权），不出站、不共享第三方；无敏感信息入库 |
| 领域合规（未成年人） | Pass with note | 仅新增"学习进度与轮次"派生统计，不采集身份信息、不采集在线行为、无追踪与第三方共享；按章程第 6 条完成新增字段自查，结论记录于 `research.md` R-008，**无需修订章程**（对比：002 的"在线时长"需在实施前单独走合规审查） |

**Gate 结论**：无阻塞违规，Phase 0 与 Phase 1 已完成，可进入 `/speckit.tasks`。

## Project Structure

### Documentation (this feature)

```text
specs/003-library-cycle-rounds/
├── plan.md              # 本文件（/speckit.plan 输出）
├── research.md          # Phase 0 输出
├── data-model.md        # Phase 1 输出
├── quickstart.md        # Phase 1 输出
├── contracts/api.md     # Phase 1 输出
├── checklists/          # /speckit.checklist 输出
└── tasks.md             # Phase 2 输出（/speckit.tasks 生成，本命令不创建）
```

### Source Code (repository root)

```text
backend/
├── src/app/
│   ├── models/
│   │   ├── study_round.py           # 【新增】study_rounds 表（游标 + 状态时间）
│   │   └── __init__.py              # 【改】注册 StudyRound
│   ├── services/
│   │   ├── round_service.py         # 【新增】轮次：创建 / 游标推进 / 覆盖 / 完成 / 补记 / 进度
│   │   ├── study_service.py         # 【改】取词由"排除全部历史"改为"本轮游标取词"；耗尽即开新轮
│   │   ├── quiz_service.py          # 【改】finish_daily_quiz 后向 round_service 发"当日测验完成"信号
│   │   └── home_service.py          # 【改】summary 增加 completed_rounds / current_round
│   ├── schemas/
│   │   ├── home.py                  # 【改】HomeSummary 扩字段
│   │   └── study.py                 # 【改】TodayStudyResponse 扩 round 字段
│   ├── api/
│   │   ├── home.py                  # 【改】响应模型同步（签名不变）
│   │   └── study.py                 # 【改】响应模型同步（签名不变）
├── alembic/versions/
│   └── 004_study_rounds.py          # 【新增】建表（不回填历史账号）
├── scripts/
│   └── seed_round_cursor.py         # 【新增】本地造数：把游标推到接近词库末尾（仅供 quickstart 场景 A/B/D/E）
└── tests/
    ├── unit/test_round_service.py       # 【新增】游标推进 / 开新轮 / 覆盖 / 完成 / 补记
    ├── contract/test_rounds_contract.py # 【新增】两个端点的新字段契约
    └── integration/test_round_cycle.py  # 【新增】耗尽 → 新一轮 → 轮次完成 → 历史不变

frontend/
├── src/
│   ├── api/home.ts                  # 【改】HomeSummary 类型增加 completed_rounds / current_round
│   ├── api/study.ts                 # 【改】TodayStudyResponse 类型增加 round
│   ├── pages/HomePage.vue           # 【改】新增「已完成 N 轮」卡片 + 大字体建议文案
│   └── pages/TodayStudyPage.vue     # 【改】进度区显示「第 N 轮 · 本轮已学 X / Y」
```

**Structure Decision**: 沿用 001 确立的 Web application 结构（backend / frontend 分离，后端托管前端产物）。本次改动全部落在既有分层内，不新增目录；后端新增 1 个模型 + 1 个服务模块，前端仅改类型与两个页面。

## Phases

### Phase 0: Outline & Research

产物：[research.md](./research.md) —— 轮次建模（独立表 + 游标，否决归属表）、两段式完成判定、轮末补记触发点、**不考虑历史账号**（迁移仅建表、不回填）、接口扩字段策略、测试策略、合规自查。Technical Context 无未知项。

### Phase 1: Design & Contracts

产物：
- [data-model.md](./data-model.md) —— `study_rounds` 字段 / 约束 / 部分唯一索引、状态机与不变量、迁移规则（仅建表、不回填历史账号）
- [contracts/api.md](./contracts/api.md) —— `GET /home/summary` 与 `GET /study/today` 的新增字段、不变端点清单、前端消费约定
- [quickstart.md](./quickstart.md) —— 场景 A–G 端到端验证（含造数据与回归项）

### Phase 2（不在本命令范围）

`/speckit.tasks` 生成 `tasks.md`：迁移 → 模型 → 服务（TDD：失败测试先行）→ 接口与契约测试 → 前端展示 → 集成验证 → 本地冒烟。

## Complexity Tracking

> 无 Constitution Check 违规，本节无需填写。
