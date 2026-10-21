# Implementation Plan: 初中英语语法学习（大纲 · 学卡 · 练习）

**Branch**: `006-grammar-study` | **Date**: 2026-10-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-grammar-study/spec.md`

## Summary

在单词模块之外新增并列的语法板块：学生按中考考点的语法大纲（21 模块 / 82 张学习卡，覆盖 85 个考点）浏览知识点 → 打开学卡走"猜一猜 → 讲解（规则 / 对比 / 速记）→ 学后检测"三段式学习 → 针对该知识点做题库练习（L1 识别 → L2 变形 → L3 陷阱 递进，即时判分 + 解析 + 错因）→ 答错的知识点回链进语法错题本，可跳回学卡重学，连续答对达标后自动移出。

技术路径：完全沿用现有技术栈 —— **FastAPI + SQLAlchemy 2 + Alembic + SQLite** 新增 4 张学习记录表（迁移 007）与 8 个 `/api/grammar/*` 端点；**Vue 3 + Vite + TypeScript + Tailwind + Pinia** 新增大纲页、学卡页、练习页三个页面与语法接口封装、语法 store、两个组件，导航新增「语法」入口。不引入任何新依赖，不需要公网资源（语法学习无音频）。

语法内容层（`grammar_points` / `grammar_questions` / `grammar_options` 与种子导入，迁移 006）已落地并通过测试，本轮在其上构建服务层、接口层与前端，并把三条规则落到服务层单一入口并配定向测试：掌握只由学后检测全对判定（FR-006）、答案在作答前不下发（FR-007）、错题回链与连续答对移除（FR-012/FR-013）。

## Technical Context

**Language/Version**: Python 3.12（后端）；TypeScript 5.6 + Node 20（前端构建）

**Primary Dependencies**: FastAPI 0.115+, SQLAlchemy 2.0+, Alembic 1.13+, Pydantic v2, pytest + pytest-cov（后端）; Vue 3.5 + Vite 5 + vue-router 4 + Pinia 2 + Tailwind CSS 3 + Vitest 2（前端）。**本轮不新增依赖**（R-010）

**Storage**: SQLite 单文件（`data/app.db`，WAL）；语法内容表与学习记录表同库，学习记录通过 `user_id` / `point_id` 外键关联

**Testing**: pytest（unit / contract / integration，真实 SQLite + TestClient，markers 必填）；Vitest + @vue/test-utils（组件与 store）；`vue-tsc --noEmit` 类型检查

**Target Platform**: Linux 服务器 Docker 单容器（后端托管前端静态产物）；客户端为现代浏览器，视口 360 / 768 / 1440

**Project Type**: Web application（前后端分离 + 后端托管前端构建产物）

**Performance Goals**: 大纲页一次返回全部知识点（82 条）与状态聚合，本地 SQLite 下 p95 < 300ms；判分请求在一次事务内完成作答、计数、错题本与进度更新，即时返回（SC-003）

**Constraints**: 单容器部署、无额外数据库服务；语法与单词两条链路互不影响（FR-020）；窄屏不得出现横向滚动；不收集任何新的个人信息；不得削弱单词模块既有约束（R-001）

**Scale/Scope**: 82 个知识点 / 约 747 道题 / 2988 个选项；账号规模个人·班级级（< 1000 账号，日活 < 200）；新增 3 个页面、8 个接口、4 张表、1 个迁移

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 章程条款 | 判定 | 落实方式 |
|---|---|---|
| I 库优先（模块自包含） | Pass | 后端新增自包含 `grammar_service`（出题、判分、结算、错题回链、掌握判定）与 `api/grammar.py`、`schemas/grammar.py`，与单词模块的 study/quiz/wrong_word 服务完全解耦；前端语法三个页面与语法 store 独立成模块，不改写既有页面（仅在导航登记入口） |
| II 契约先行 | Pass | Phase 1 先产出 `contracts/api.md`（8 个端点、字段、错误码），实现、前端与契约测试均以该文件为准；错误码同步登记到 `errors.py` |
| III 测试先行 | Pass | 先写失败测试再实现：掌握判定（全对才掌握）、答案保护（出题响应不含 `is_correct`/`explanation`/`feedback`）、错题回链与连续答对移除；前端先写题卡反馈与状态徽章的组件测试 |
| IV 集成测试覆盖关键接缝 | Pass | 用真实 SQLite（已含语法种子）+ TestClient 跑"打开学卡 → 检测 → 练习 → 答错入错题本 → 回链重学 → 连续答对移出"全链路集成测试；契约测试覆盖 401/404/409/422，禁用 mock 掩盖接线 |
| V 可观测性 / 版本 / 简洁 | Pass | 结构化日志覆盖练习发起、判分结果、错题本增删（含 user_id 与 point_id，不含身份信息）；沿用语义化版本；刻意拒绝的复杂度见下方 Complexity Tracking |
| 附加约束：技术栈由 plan 决定 | Pass | 技术栈首次出现在本文件；`spec.md` 保持技术中立，未出现框架名 |
| 附加约束：依赖需论证 | Pass | 本轮零新增依赖（R-010），未引入渲染库、状态机库或任何第三方服务 |
| 附加约束：数据与安全 | Pass | 不新增任何注册 / 个人字段，语法侧仅存"用户标识 + 知识点标识 + 计数"；沿用既有 JWT 与口令哈希方案，密钥不入库；数据仅存自有服务器 |
| 领域合规（未成年人） | Pass | 未收集邮箱、真实姓名、学校、班级等身份信息；无第三方共享、无行为追踪、无个性化推荐；语法日志不含身份信息 |

**Gate 结论**：无阻塞违规，进入 Phase 0（Phase 1 设计后复查：新增 4 张表不改变既有表，无破坏性变更，结论维持 Pass）。

## Project Structure

### Documentation (this feature)

```text
specs/006-grammar-study/
├── spec.md              # 需求（技术中立）
├── plan.md              # 本文件
├── research.md          # Phase 0 输出（12 项决策）
├── data-model.md        # Phase 1 输出（内容层 3 表 + 学习记录层 4 表）
├── quickstart.md        # Phase 1 输出（场景 A–H 端到端验证）
├── contracts/api.md     # Phase 1 输出（8 个端点契约）
└── tasks.md             # Phase 2 输出（/speckit.tasks 生成，本命令不创建）
```

### Source Code (repository root)

```text
backend/
├── src/app/
│   ├── main.py                  # 修改：注册 grammar 路由（prefix=/api）
│   ├── errors.py                # 修改：登记 grammar_* / no_grammar_questions 错误码
│   ├── models/grammar.py        # 已存在（迁移 006）：GrammarPoint / GrammarQuestion / GrammarOption
│   ├── models/grammar_progress.py  # 新增：GrammarAttempt / GrammarAnswer
│   │                                #       GrammarPointProgress / GrammarWrongPoint
│   ├── schemas/grammar.py       # 新增：与 contracts/api.md 对齐的 Pydantic v2 模型
│   ├── services/grammar_service.py  # 新增：出题、判分、结算、掌握判定、错题回链
│   └── api/grammar.py           # 新增：8 个端点（prefix=/grammar, tags=["grammar"]）
├── alembic/versions/
│   └── 007_grammar_progress.py  # 新增：4 张表 + 索引 + CHECK（存在则跳过）
└── tests/
    ├── unit/test_grammar_service.py      # 判分 / 掌握判定 / 错题规则
    ├── contract/test_grammar_contract.py # 字段形状、答案保护、401/404/409/422
    └── integration/test_grammar_flow.py  # 学卡 → 检测 → 练习 → 错题闭环

frontend/
├── src/
│   ├── api/grammar.ts                  # 新增：8 个接口封装（复用 client.ts）
│   ├── stores/grammar.ts               # 新增：大纲、错题本（跨页复用）
│   ├── pages/GrammarOutlinePage.vue    # 新增：/grammar
│   ├── pages/GrammarCardPage.vue       # 新增：/grammar/:pointId
│   ├── pages/GrammarPracticePage.vue   # 新增：/grammar/:pointId/practice
│   ├── components/GrammarPointItem.vue # 新增：大纲条目 + 状态徽章
│   ├── components/GrammarQuestionCard.vue # 新增：题干 + 选项 + 判分反馈
│   ├── components/AppShell.vue         # 修改：导航新增「语法」
│   └── router/index.ts                 # 修改：3 条路由
└── tests/unit/
    ├── grammarOutline.spec.ts          # 大纲分组与状态徽章
    ├── grammarQuestionCard.spec.ts     # 作答反馈与解析展示
    └── grammarStore.spec.ts            # store 加载与错题计数
```

**Structure Decision**: 沿用既有 Web application 结构（前后端分离目录，后端托管前端构建产物）。后端按既有 `models / schemas / services / api` 四层新增语法模块，与单词模块平级而非混入；前端页面、组件、接口封装、store 均新增独立文件，对既有文件的改动仅限 `AppShell.vue` 导航与 `router/index.ts` 路由表两处登记。

## Phases

### Phase 0: Outline & Research

产物：[research.md](./research.md) —— 12 项决策：是否复用单词测验表（新建语法专用表）、掌握状态的判定与存储、轮次建模（card/bank 同表）、错题回链粒度与移除阈值、出题是否洗牌（不洗牌）、答案保护策略、作答入参用选项键、大纲数据来源、前端状态组织、技术栈与零新增依赖、页面与组件划分、迁移策略。Technical Context 无 NEEDS CLARIFICATION。

### Phase 1: Design & Contracts

产物：
- [data-model.md](./data-model.md) —— 内容层 3 表（已存在）与学习记录层 4 表（新增）的字段、约束、索引、状态流转与规则常量
- [contracts/api.md](./contracts/api.md) —— 8 个 REST 端点、请求/响应结构、8 个错误码、契约测试要点
- [quickstart.md](./quickstart.md) —— 场景 A–H 端到端验证步骤与预期结果

**Post-Design Constitution Check**：新增 4 张表与 8 个端点均为**新增**，不修改既有表结构与既有接口；语法与单词共用认证与数据库但业务链路独立；未引入依赖与复杂度 —— 结论维持 Pass。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

本章程检查无违规项，无需填写。设计阶段刻意拒绝的复杂度：

- 不复用 / 放宽单词测验表的 CHECK 与外键约束（改为新建语法专用表），避免削弱既有 invariants；
- 不引入随机洗牌与种子状态（题库按 L1→L2→L3 递进顺序出题）；
- 不新增独立语法错题本页面（作为大纲页的筛选视图 + 学卡跳转复用）；
- 不引入 Markdown 渲染库（教研内容是结构化 JSON，按 `card_type` 模板渲染）；
- 不新增跨知识点混合练习、练习历史回顾、知识点搜索（首版不做）。
