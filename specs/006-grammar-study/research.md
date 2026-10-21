# Research: 初中英语语法学习（大纲 · 学卡 · 练习）

**Feature**: 006-grammar-study | **Date**: 2026-10-19

本文件解决 Technical Context 中的全部未知项，并给出每个决策的理由与被否决的备选方案。语法数据层（知识点 / 题目 / 选项三张表与种子导入）已随迁移 006 落地，本轮研究面向其上的服务层与接口层。

---

## R-001 语法学习数据是否复用单词模块的测验表？

**Decision**: 不复用。新建 `grammar_attempts` / `grammar_answers` 两张语法专用表。

**Rationale**: 既有的 `quiz_attempts.kind` 受 CHECK 约束限制为 `('daily','review','archive')`，`quiz_answers.question_type` 受 CHECK 约束限制为 `('en2zh','zh2en')`，且 `quiz_answers.word_id` 是 `NOT NULL` 且外键指向 `words.id` —— 语法题三个条件全部不满足。放宽约束需要改动既有表与既有迁移，会让单词模块的 invariants（kind 决定取题集合、word_id 必填）失去保护。

**Alternatives considered**:
- 复用 `quiz_attempts` + 新增迁移放宽 CHECK 与外键 → 否决：为语法需求削弱单词模块的约束，违反章程 V（简洁）与"破坏性变更需迁移与回滚方案"。
- 用一张通用的 `answers` 表加 `module` 字段区分 → 否决：跨模块共享答题表会让"单词答错进单词错题本、语法答错进语法错题本"的分流逻辑纠缠在一处。

---

## R-002 掌握状态如何存储与判定？

**Decision**: 每个用户 × 每个知识点一行 `grammar_point_progress`，状态枚举 `not_started / learning / mastered`；**只有学后检测（卡内题）全部答对**才置为 `mastered`，练习结果不改变掌握状态。

**Rationale**: 掌握是"学会没学会"的判断，学后检测紧贴刚讲完的规则，是可靠的即时验证；题库练习是巩固手段，其答错反映的是"会用不会用"，若让练习把已掌握打回学习中，会造成状态反复、大纲页忽明忽暗，学生无法建立稳定预期。练习答错仍有出口：进语法错题本（R-004）。

**Alternatives considered**:
- 练习也参与掌握判定（如连续答对 N 次才掌握）→ 否决：掌握路径变成两条，规则难以向学生解释，且需要额外阈值调参。
- 不存状态、按"是否做过检测"实时计算 → 否决：大纲页一次要渲染 82 个知识点，实时聚合会放大查询开销，且历史统计（答对数）无处存放。

---

## R-003 学习轮次如何建模（学后检测与题库练习是否同一张表）？

**Decision**: 同一张 `grammar_attempts`，用 `source` 区分 `card`（学后检测）与 `bank`（题库练习）；一次学后检测与一次题库练习都是一轮，共用同一套 `start → answer → finish` 流程与同一对判分接口。

**Rationale**: 两者的流程完全同构（出题、逐题判分、结算），共用轮次表让判分与结算只有一份实现，前端也只有一套答题交互。差异只有取题范围（卡内题 / 题库题）与结算语义（是否判定掌握），用 `source` 字段区分即可。

**Alternatives considered**:
- 学后检测不建轮次，直接写答题流水 → 否决：无法判断"检测是否全部答对"（R-002 的掌握判定需要一次完整轮次的边界）。
- 两张轮次表分开 → 否决：结构相同却两套代码，违反 YAGNI。

---

## R-004 错题回链的粒度与移除规则？

**Decision**: 题目级携带 `error_tag`（指向知识点），答错时按 `error_tag` 把**知识点**记入 `grammar_wrong_points`；移除规则与单词错题本保持一致：连续答对 2 次移出，答错归零。

**Rationale**: 语法的最小可重学单元是知识点（回链到学卡才有意义），回链到单题没有可操作的下一步。沿用单词模块已经验证过的 `wrong_count + correct_streak` 与阈值 2，学生对两个板块的手感一致，且已有代码（`wrong_word_service` 的 touch / 移除逻辑）可直接参照实现。

**Alternatives considered**:
- 复用 `wrong_words` 表 → 否决：`word_id → words.id NOT NULL`，语法知识点没有单词 id。
- 按题目级存错题 → 否决：错题本会迅速膨胀成"题目流水"，失去"回去补哪个知识点"的指引作用。

---

## R-005 练习出题是否随机洗牌？

**Decision**: 不洗牌。按 `level`（L1 识别 → L2 变形 → L3 陷阱）与 `order_index` 递增顺序出题。

**Rationale**: 每个知识点题库固定 6 题（L1/L2/L3 各 2 题），层级递进本身就是教研设计的出题顺序 —— 先认得出、再会变化、最后识破陷阱。洗牌反而破坏递进。单词模块洗牌是为了防止"背顺序"，而语法题库一次练习覆盖该点全部题目且量小，背顺序的问题不成立。

**Alternatives considered**:
- 沿用单词模块的 `random.Random(seed)` 洗牌 → 否决：破坏 L1→L2→L3 的递进设计，且引入无必要的随机种子状态。

---

## R-006 如何在判分前不泄露答案？

**Decision**: 出题接口只返回选项的 `key` 与 `text`；`is_correct`、`explanation`、错项 `feedback` 一律不下发，仅在作答后的判分响应中返回（正确项、解析、所选错项的错因）。

**Rationale**: 与单词测验既有约定一致（`QuizQuestion` 只含 `prompt + options`，判分后才给 `correct_index`）。前端若提前拿到正确项，学生可用开发者工具直接看答案，练习与检测就失去意义。

**Alternatives considered**:
- 下发完整选项含 `is_correct`，前端隐藏 → 否决：答案进了客户端即视为泄露，无法靠 UI 隐藏保证。

---

## R-007 作答入参用选项下标还是选项键？

**Decision**: 用选项键（`choice_key`，取 `A`–`D`）。

**Rationale**: 语法题目与选项的稳定标识是种子里的 `key` 字段，前端渲染的也是 A/B/C/D；用键可以让判分日志、错题错因（"你选了 B，错在…"）与教研内容直接对齐，避免下标与键之间的映射转换引入错位。

**Alternatives considered**:
- 沿用单词模块的 `choice_index`（0–3）→ 否决：语法选项在种子里以键组织，转下标需要在服务端与前端各维护一次排序假设，是纯粹的复杂度。

---

## R-008 大纲页的数据来源？

**Decision**: 直接以 `grammar_points` 为准（按 `module` + `order_index` 排序分组），左连接当前用户的进度与错题本补齐状态；不额外维护一份"85 个大纲知识点"的清单。

**Rationale**: 合并卡通过 `covers` 字段记录它覆盖的多个大纲编号，82 张卡已完整覆盖 85 个考点。再引入一份大纲清单会出现两份事实来源，需要额外的对账逻辑与测试。

**Alternatives considered**:
- 以 `syllabus.md` 的 85 个编号为大纲、卡片按 `covers` 挂载 → 否决：需要把 markdown 大纲变成可查询数据（新增表或新增解析），与"不引入第二份事实来源"冲突。

---

## R-009 前端状态如何组织？

**Decision**: 新增 `stores/grammar.ts` 持有大纲与错题本（跨页面复用的列表数据）；学卡与练习的轮次状态放在页面内（一次性的作答流程），不进 store。

**Rationale**: 与现有代码一致：跨页面复用的列表（单词错题本）走 store，一次性流程（今日测验的答题过程）留在页面。语法的三个页面共享大纲与错题本，进 store 可避免返回大纲页时重新请求与状态闪烁。

**Alternatives considered**:
- 全部走 store → 否决：轮次作答状态是页面级临时状态，进 store 需要额外的清理时机，容易残留。
- 全部不进 store → 否决：大纲页 → 学卡 → 返回大纲，每次都要重新拉取，进度徽章会闪。

---

## R-010 技术栈与依赖？

**Decision**: 完全沿用现有技术栈，不新增任何依赖 —— 后端 FastAPI + SQLAlchemy 2 + Alembic（新增迁移 007）、Pydantic v2 schema、pytest（真实 SQLite）；前端 Vue 3 + vue-router 4 + Pinia 2 + Tailwind 3 + Vitest。

**Rationale**: 语法模块与单词模块是同一应用内的并列板块，共用认证、数据库与前端骨架。新增依赖（如状态机库、题目渲染库）没有解决任何现有能力缺口。

**Alternatives considered**:
- 引入 Markdown 渲染库来渲染讲解卡面 → 否决：教研内容是结构化 JSON（规则 / 信号词 / 公式 / 锚例句 / 陷阱），用模板渲染更可控，也不需要解析 Markdown 的额外依赖与安全策略。

---

## R-011 前端新增哪些页面与组件？

**Decision**: 三个页面 —— 大纲页 `/grammar`、学卡页 `/grammar/:pointId`、练习页 `/grammar/:pointId/practice`；两个组件 —— 大纲条目卡（含状态徽章）、语法题卡（题干 + 选项 + 判分反馈）；导航新增"语法"入口；不新增错题本独立页面（错题列表作为大纲页的一个筛选视图 + 学卡跳转）。

**Rationale**: 三个页面对应 US1/US2/US3 三条主路径，边界清晰。错题本（US4）的入口是"跳回学卡"，本身只需要列表，做成大纲页的筛选视图即可复用大纲的状态徽章与跳转逻辑，避免第 4 个页面带来的导航膨胀。

**Alternatives considered**:
- 独立错题本页 `/grammar/wrong` → 否决：与大纲页结构高度重合（列表 + 跳转），独立页面会让底部导航从 7 项再增一项，窄屏更拥挤。
- 学卡与练习合并为单页内的分段 → 否决：两者是"学"与"练"两个意图，合并会让返回键语义含糊。

---

## R-012 迁移怎么做？

**Decision**: 新增单个迁移 `007_grammar_progress.py`，创建 4 张表（`grammar_attempts`、`grammar_answers`、`grammar_point_progress`、`grammar_wrong_points`）及索引与 CHECK 约束；沿用既有迁移的"存在则跳过"幂等写法，不改动 001–006 任何已执行迁移。

**Rationale**: 语法内容表（006）与学习记录表（007）职责不同：前者是随系统发布的教研内容，后者是用户产生的数据。分开后重新导入内容种子不会牵动用户数据，也符合既有惯例（002 导词表、003 加字段、004 加轮次表）。

**Alternatives considered**:
- 把 4 张表并入 006 → 否决：006 已执行（库里已有数据），改已执行迁移会破坏既有环境的升级路径。
- 复用 `study_rounds` 的轮次游标机制 → 否决：语法不按"每日集合"推进，没有轮次游标的必要。
