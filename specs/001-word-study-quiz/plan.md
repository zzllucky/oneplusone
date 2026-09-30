# Implementation Plan: 中考英语单词学习测验与错题本

**Branch**: `001-word-study-quiz` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-word-study-quiz/spec.md`

## Summary

面向初中学生的中考英语单词记忆 Web 站点：登录名 + 密码 + 昵称自由注册登录 → 设置每日背词目标 → 系统按目标分配当日单词并逐词学习（含发音）→ 全部浏览后解锁今日测验（英译中 / 中译英四选一）→ 答错的单词进入错题本 → 错题专项练习答对才从错题本移除。

技术路径：**FastAPI + SQLAlchemy 2.x + Alembic + SQLite（WAL）** 提供 REST 接口并托管前端静态产物；**Vue 3 + Vite + TypeScript** 实现响应式单页应用；**Docker Compose 单容器**部署；词表（约 1600 词）作为种子数据由 Alembic 迁移导入；单词发音由**服务端代理第三方公共发音接口**（带磁盘缓存与 2 秒超时），失败或无结果时前端降级为浏览器语音合成。

三条硬性业务规则在架构上用**职责分离的服务函数 + 定向测试**保证：浏览完成才解锁测验（FR-018/FR-019）、今日测验答对不删错题（FR-026）、错题唯一移除途径为专项练习答对（FR-031）。

## Technical Context

**Language/Version**: Python 3.12（后端）；TypeScript 5.x + Node 20（前端构建）

**Primary Dependencies**: FastAPI 0.115+, SQLAlchemy 2.0+, Alembic 1.13+, Pydantic v2 / pydantic-settings, passlib[bcrypt]（口令哈希）, PyJWT（JWT）, httpx（发音代理）; Vue 3 + Vite 5 + vue-router 4 + Pinia 2 + Tailwind CSS 3

**Storage**: SQLite 单文件（`data/app.db`），开启 WAL 与 `busy_timeout`；词表与用户数据同库；发音音频缓存落磁盘目录

**Testing**: pytest + pytest-cov + FastAPI TestClient（后端单元 / 契约 / 集成）；Vitest + @vue/test-utils（前端组件与状态）；Playwright 可选 E2E（quickstart 场景自动化候选）

**Target Platform**: Linux 服务器 Docker 容器（后端 uvicorn 单进程）；客户端为现代浏览器（桌面 Chrome/Edge、移动 Safari/Chrome），视口 360 / 768 / 1440

**Project Type**: Web application（前后端分离 + 后端托管前端静态产物）

**Performance Goals**: 学习页与测验页交互即时响应；接口 p95 < 300ms（SQLite 本地读写远低于该量级）；发音请求 2s 内未返回即降级；首屏可交互 < 2s（本地网络）

**Constraints**: 单容器部署、无额外数据库服务；公网可访问（发音代理需要）；口令不可逆哈希且不出库；窄屏不得出现横向滚动；错题本删除规则不得被任何旁路破坏

**Scale/Scope**: 词库约 1600 词；账号规模个人 / 班级级（< 1000 账号，日活 < 200）；8 个页面、约 20 个接口

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 章程条款 | 判定 | 落实方式 |
|---|---|---|
| I 库优先（模块自包含） | Pass | 后端按 `models / services / api` 分层：`study_service`（每日分配与浏览）、`quiz_service`（出题与批改）、`wrong_word_service`（错题本唯一增删口），各自可独立测试 |
| II 契约先行 | Pass | Phase 1 先产出 `contracts/api.md`（全部端点、请求/响应字段、错误码），实现与前端集成均以该文件为准 |
| III 测试先行 | Pass | 三条硬性规则先写失败用例（测验锁定、答对不删错题、专项答对才删），再实现 |
| IV 集成测试覆盖关键接缝 | Pass | 用真实 SQLite 文件 + TestClient 跑"学习 → 测验 → 错题入本 → 专项练习 → 错题移除"链路集成测试，不使用 mock 掩盖接线 |
| V 可观测性 / 版本 / 简洁 | Pass | 结构化日志（请求、测验结果、发音代理失败）；语义化版本；无状态 JWT + 单容器，不引入缓存中间件、消息队列等额外组件 |
| 附加约束：技术栈由 plan 决定 | Pass | 技术栈首次出现在本文件；spec.md 保持技术中立 |
| 附加约束：依赖需论证 | Pass | 依赖清单见 research.md R-012，均为必需项（Web 框架、ORM、迁移、口令哈希、JWT、HTTP 客户端、前端框架与构建） |
| 附加约束：数据与安全 | Pass | 仅收集登录名 + 昵称 + 口令哈希（不收集邮箱、真实姓名、学校等）；bcrypt 哈希；JWT 密钥由环境变量注入且不入库；数据仅存自有服务器 |
| 领域合规（章程 TODO(PROJECT_DOMAIN)） | Pass with note | 目标用户为初中生（未成年人），本版按**最小必要**收集（邮箱 + 密码，无真实身份信息）、无第三方共享、无行为追踪；如需接入真实学校/班级数据，须先修订章程补充合规条款 |

**Gate 结论**：无阻塞违规，进入 Phase 0。

## Project Structure

### Documentation (this feature)

```text
specs/001-word-study-quiz/
├── plan.md              # 本文件
├── research.md          # Phase 0 输出
├── data-model.md        # Phase 1 输出
├── quickstart.md        # Phase 1 输出
├── contracts/api.md     # Phase 1 输出
└── tasks.md             # Phase 2 输出（/speckit.tasks 生成，本命令不创建）
```

### Source Code (repository root)

```text
backend/
├── src/app/
│   ├── main.py               # FastAPI 应用装配、静态资源托管
│   ├── config.py             # 环境变量与配置（JWT_SECRET、DB 路径、发音超时等）
│   ├── db.py                 # SQLAlchemy engine/session（SQLite WAL）
│   ├── models/               # users, settings, words, daily_sets, daily_set_items,
│   │                         # quiz_attempts, quiz_answers, wrong_words
│   ├── schemas/              # Pydantic 请求/响应模型（与 contracts/api.md 对齐）
│   ├── services/             # auth_service, settings_service, study_service,
│   │                         # quiz_service, wrong_word_service, pronounce_service
│   ├── api/                  # auth.py, settings.py, home.py, study.py, quiz.py,
│   │                         # wrong_words.py, pronounce.py
│   └── security.py           # 口令哈希与 JWT 签发/校验
├── alembic/versions/         # 001 建表、002 导入词表种子
├── seeds/words.txt           # 内置中考词表种子数据（统一格式：单词 词性.释义 | 短语1；短语2）
├── tests/
│   ├── unit/
│   ├── contract/
│   └── integration/
└── pyproject.toml

frontend/
├── src/
│   ├── api/                  # 后端接口封装
│   ├── components/           # WordCard、QuizQuestion、PronounceButton 等
│   ├── pages/                # 注册/登录/首页/设置/学习/测验/错题本/专项练习
│   ├── stores/               # Pinia（auth、study、wrongWords）
│   ├── router/index.ts       # 8 个页面路由 + 登录守卫
│   └── composables/useSpeech.ts  # 浏览器语音降级
├── tests/
├── index.html
└── package.json

docker-compose.yml
Dockerfile                    # 多阶段：构建前端 → 复制产物 → 运行 uvicorn
```

**Structure Decision**: 采用 Web application 结构（前后端分离目录，后端托管前端构建产物）。单容器部署，无独立数据库服务，SQLite 数据文件与发音缓存目录以卷挂载持久化。

## Phases

### Phase 0: Outline & Research

产物：[research.md](./research.md) —— 词表导入与替换策略、口令与会话方案、发音代理与降级、SQLite 并发与"当日"边界、测验出题与干扰项、错题本删除规则的服务层隔离、测试策略。全部 NEEDS CLARIFICATION 已在该文件解决（Technical Context 无未知项）。

### Phase 1: Design & Contracts

产物：
- [data-model.md](./data-model.md) —— 8 张表的字段、约束、索引、状态流转
- [contracts/api.md](./contracts/api.md) —— 约 20 个 REST 端点、请求/响应结构、错误码
- [quickstart.md](./quickstart.md) —— 场景 A–H 端到端验证步骤与预期结果

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

本章程检查无违规项，无需填写。设计阶段刻意拒绝的复杂度：不引入 Redis / 消息队列 / 独立数据库容器 / 前端 SSR；会话采用无状态 JWT 而非服务端会话表；解锁状态由数据实时计算而非冗余字段。
