# Implementation Plan: 学习日历总结

**Branch**: `002-study-calendar-summary` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-study-calendar-summary/spec.md`

## Summary

新增站内「总结」页：以**月历**呈现学生每天的学习情况（灰色 = 无记录、浅绿 = 打开过但没学、深绿 = 有学习且按学习量分档加深），点击有记录的日期可看当天**四项明细**（学习单词数、今日测验对 / 错、错题本专项练习、错题库专项练习），并给出**当月汇总**与**连续学习天数**。

技术路径：在既有 FastAPI + SQLAlchemy 2.x + Alembic + SQLite 与 Vue 3 + Vite 栈上，新增一个只读域 `summary`（`summary_service` + `api/summary.py` + `schemas/summary.py`），**不新增任何业务表**——所有数字按"用户 + 日期"从既有的 `daily_sets` / `daily_set_items` / `quiz_attempts` / `quiz_answers` 聚合得出（research R-001）；迁移 `005` 只补 3 个查询索引。新增 2 个只读端点（`GET /api/summary/month`、`GET /api/summary/day`）与 1 个前端页面，**不改任何既有端点、不新增第三方依赖**。

> **范围变更（2026-09-30）**：「在线时长」已从本功能整体移除（不采集 / 不存储 / 不展示），单日明细由五项改为四项；浅绿改用既有的"当日学习集合是否存在"判定，因此**未新增任何个人信息字段**，不触发章程「领域合规 · 第 6 条」的前置审查。详见 `spec.md` 变更记录与合规结论。

## Technical Context

**Language/Version**: Python 3.12（后端）；TypeScript 5.x + Node 20（前端构建）

**Primary Dependencies**: FastAPI 0.115+、SQLAlchemy 2.0+、Alembic 1.13+、Pydantic v2；Vue 3 + Vite 5 + vue-router 4 + Pinia 2 + Tailwind CSS 3（均为既有依赖，**本次零新增**，含不引入日历组件库——research R-010）

**Storage**: SQLite 单文件（`data/app.db`，WAL）——**不新增业务表**；迁移 `005` 仅新增 `quiz_attempts(user_id, kind, study_date)`、`quiz_attempts(user_id, finished_at)`、`quiz_answers(answered_at)` 三个索引

**Testing**: pytest + FastAPI TestClient（unit / contract / integration 三层）；Vitest（前端，按需）

**Target Platform**: Linux 服务器 Docker 单容器（uvicorn）；客户端现代浏览器，视口 360 / 768 / 1440

**Project Type**: Web application（前后端分离，后端托管前端静态产物）

**Performance Goals**: 总结页 3 秒内看到当月日历（SC-001）、点击日期 1 秒内看到明细（SC-002）；按月一次性 `GROUP BY` 聚合、禁止按天循环查询，接口 p95 < 300ms 与既有目标一致

**Constraints**: 只读聚合，不写入 / 不修改 / 不删除任何既有数据；不新增采集字段、不上报任何行为数据；既有端点字段与错误码不变；不引入新依赖

**Scale/Scope**: 账号 < 1000，日活 < 200；改动面 = 1 个新服务模块 + 1 个新路由 + 1 个 schema + 1 个迁移（索引）+ 1 个造数脚本 + 1 个前端页面 + 路由与导航各 1 处注册

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 章程条款 | 判定 | 落实方式 |
|---|---|---|
| I 库优先（模块自包含） | Pass | 新增 `summary_service` 单一职责：按"用户 + 日期"聚合四类数据、计算着色等级 / 连续天数；`api/summary.py` 只做参数校验与 schema 组装；不改动既有服务 |
| II 契约先行 | Pass | Phase 1 先产出 `contracts/api.md`（2 个只读端点的入参、响应字段、错误码、前端消费与兜底约定），实现与前端均以该文件为准 |
| III 测试先行 | Pass | 先写失败用例：① 学过 / 只打开 / 无记录三类日期的着色与分档；② 四项明细与实际行为一致；③ 无记录日期返回 `has_record=false` 而非 404；④ 连续天数"当天未学不归零"；再实现 |
| IV 集成测试覆盖关键接缝 | Pass | 用真实 SQLite + HTTP 跑"学习 → 浏览 → 测验 → 两类专项练习 → 查月 / 日接口"，禁止 mock 掩盖聚合 SQL 与接口接线 |
| V 可观测性 / 版本 / 简洁 | Pass | 聚合查询写结构化日志（月 / 日参数与耗时）；变更记入 `CHANGELOG.md`；**简洁**：不建汇总表、不引入日历库、不新增依赖（YAGNI，research R-001 / R-010） |
| 附加约束：技术栈由 plan 决定 | Pass | 技术栈仅出现在本文件；`spec.md` 保持技术中立 |
| 附加约束：依赖需论证 | Pass | **零新增依赖**，既有栈已足够（research R-001 / R-010 已书面否决日历组件库与物化方案） |
| 附加约束：数据与安全 | Pass | 汇总数据仅本人可见（随既有账号鉴权返回），不出站、不共享第三方；无敏感信息入库 |
| 领域合规（未成年人） | Pass（无需审查） | 本功能**不采集、不存储、不展示任何在线时长**，也不采集页面内容 / 点击流；浅绿复用既有"当日学习集合是否存在"，**未新增任何个人信息字段**，仅新增查询索引 → **不触发**第 6 条前置审查；结论记录于 `spec.md`「合规结论」、`checklists/requirements.md` 与本文件（research R-007） |

**Gate 结论**：无阻塞违规，Phase 0 与 Phase 1 已完成，可进入 `/speckit.tasks`。

## Project Structure

### Documentation (this feature)

```text
specs/002-study-calendar-summary/
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
│   ├── services/
│   │   └── summary_service.py        # 【新增】按月 / 按日聚合、着色与连续天数
│   ├── schemas/
│   │   └── summary.py                # 【新增】MonthSummary / DaySummary 响应模型
│   ├── api/
│   │   ├── summary.py                # 【新增】/summary/month、/summary/day（只读）
│   │   └── __init__.py / main.py     # 【改】注册 summary 路由（前缀 /api）
├── alembic/versions/
│   └── 005_summary_query_indexes.py  # 【新增】3 个查询索引（不建表、不回填）
├── scripts/
│   └── seed_summary_history.py       # 【新增】本地造数：生成最近 N 天的历史行为（供 quickstart）
└── tests/
    ├── unit/test_summary_service.py  # 【新增】聚合口径、着色 / 分档、连续天数
    ├── unit/test_summary_indexes.py  # 【新增】断言迁移 005 的索引真实存在（防"静默丢失"）
    ├── contract/test_summary_contract.py # 【新增】两个端点字段集合、无记录日期、参数校验
    └── integration/test_summary_flow.py  # 【新增】真实链路：行为 → 汇总 → 跨设备一致

frontend/
├── src/
│   ├── api/summary.ts                # 【新增】month / day 接口封装
│   ├── pages/SummaryPage.vue         # 【新增】月历 + 月度汇总 + 连续天数 + 单日明细
│   ├── router/index.ts               # 【改】注册 /summary 懒加载路由
│   └── components/AppShell.vue       # 【改】navItems 增加「总结」入口
```

**Structure Decision**: 沿用 001 确立的 Web application 结构（backend / frontend 分离，后端托管前端产物）。本次改动全部落在既有分层内，不新增目录；后端新增 1 个只读域（service + schema + api）与 1 个索引迁移，前端新增 1 个页面与类型封装，并注册路由与导航。

## Phases

### Phase 0: Outline & Research

产物：[research.md](./research.md) —— 实时聚合 vs 物化（否决建汇总表）、四类数据的归日口径、专项练习按 `answered_at` 归日、着色与分档阈值、历史账号无需回填、两个只读端点的接口设计、**合规结论（不触发第 6 条）**、索引与性能、测试策略、前端不引日历库。Technical Context 无未知项。

### Phase 1: Design & Contracts

产物：

- [data-model.md](./data-model.md) —— 派生实体（每日汇总 / 月度汇总 / 连续天数）的字段与口径、既有表只读引用、枚举与不变量、迁移 `005` 索引清单与 downgrade
- [contracts/api.md](./contracts/api.md) —— `GET /api/summary/month`、`GET /api/summary/day` 的入参 / 响应 / 错误码 / 前端消费与兜底约定、不变端点清单
- [quickstart.md](./quickstart.md) —— 场景 A–F 端到端验证、造数脚本用法、自动化等价覆盖与回归项（含 003 的 US4 验收 3 回归）

### Phase 2（不在本命令范围）

`/speckit.tasks` 生成 `tasks.md`：迁移索引 → 契约 / 单元测试（先失败）→ `summary_service` → 端点与契约测试 → 前端页面与导航 → 集成验证 → 本地冒烟与 `CHANGELOG`。

## Complexity Tracking

> 无 Constitution Check 违规，本节无需填写。
