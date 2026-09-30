# Feature Specification: 词库循环学习与轮次统计

**Feature Branch**: `003-library-cycle-rounds`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "单词卡一共 2000 多个，如果全部学完了会是什么效果？→ 循环学习词库的单词，但是需要增加一个功能，显示你已经完成词库多少次的学习，这个多少次是指多少轮，比如完成了 2 次词库的学习就提示完成 2 轮"

## Clarifications

### Session 2026-09-29

- Q: 一轮「完成」怎么判定？ → A: **当日测验也完成才算** —— 不仅浏览完本轮最后一个单词，还要把当天的今日测验做完，该轮才算完成（更严格，避免"刷完就跑"）
- Q: 新一轮按什么顺序取词？ → A: **按词库原顺序** —— 从词库第一个词从头再来，顺序与第一次学习完全一致（可预期、好对照）
- Q: 轮次与当前轮进度展示在哪些页面？ → A: **首页 + 学习页** —— 首页显示「已完成 N 轮」并用**加大字体**提示"建议初中会考前每天坚持学习，至少完成 10 轮"；学习页显示当前轮进度（本轮已学 / 词库总数）

## Background（问题背景）

产品内置词库共 2096 个单词。按既有规则，单词一旦进入过某天的学习集合即视为「已学」，不再参与后续分配。因此当词库被学完（最后一词进入当日集合并浏览完毕）后，系统将进入"无词可分配"状态：学习页显示"今日暂无待学习单词"，今日测验因"未浏览完全部单词"而永久无法解锁。本功能补上这一边界：词库学完后**自动进入下一轮**（按词库原顺序重新开始），并统计展示**已完成词库学习的轮数**。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 学完词库后继续有词可学 (Priority: P1)

学生在学完词库最后一个单词之后的下一个学习日进入学习页时，系统自动开启**新一轮**学习：按词库原顺序继续分配单词（本轮尚未出现的词），不再出现"今日暂无待学习单词"的空状态；当日浏览完成后，今日测验照常解锁。

**Why this priority**: 这是本功能要解决的核心缺陷——词库学完即"锁死"，学生无法继续学习，也无法再参加今日测验。

**Independent Test**: 在词库耗尽状态下（已将全部单词学完）进入次日 → 学习页出现数量等于每日目标（或剩余量）的单词 → 全部浏览后测验入口解锁并完成一轮测验；单独交付即消除"卡死"状态。

**Acceptance Scenarios**:

1. **Given** 学生已学完词库全部单词, **When** 次日进入学习页, **Then** 出现新一轮的待学习单词，页面不显示"今日暂无待学习单词"。
2. **Given** 新一轮当日集合已生成, **When** 学生浏览完当日全部单词, **Then** 今日测验解锁，可正常开始并完成测验。
3. **Given** 新一轮进行中, **When** 学生按每日目标推进多天, **Then** 每天按**词库原顺序**分配到本轮尚未学过的单词，直到该轮覆盖完整个词库。
4. **Given** 新一轮中某个单词, **When** 该单词已在本轮中出现过, **Then** 在本轮结束前不再重复分配（每轮内每个单词恰好出现一次）。
5. **Given** 学生在新一轮中途中断数日后回来, **When** 再次学习, **Then** 从本轮剩余未学的单词继续，**不重新开始一轮、不重置已有进度**。

---

### User Story 2 - 显示已完成词库学习的轮数 (Priority: P1)

学生在**首页**能看到**已完成词库学习的轮数**（"已完成 2 轮"）与坚持建议，在**学习页**能看到当前这一轮的推进程度（本轮已学 / 词库总数）。一轮的完成以"本轮最后一个单词浏览完成 **且** 当日测验完成"为准。

**Why this priority**: 循环学习如果没有轮次反馈，学生无法感知自己"刷了几遍词库"，缺少成就感与进度感，这是用户明确点名要的功能。

**Independent Test**: 完整学完第一遍词库并完成当日测验 → 首页显示"已完成 1 轮"并开始第 2 轮 → 再学完并完成测验 → 显示"已完成 2 轮"；单独交付即可作为"学习成就统计"。

**Acceptance Scenarios**:

1. **Given** 学生尚未完整学完一遍词库, **When** 查看首页, **Then** 显示已完成 **0 轮**，并标明当前处于第 1 轮。
2. **Given** 学生浏览完本轮最后一个单词**并完成当日测验**, **When** 查看首页, **Then** 已完成轮数变为 **1 轮**。
3. **Given** 学生已完整学完 2 遍词库（每遍均完成当日测验）, **When** 查看首页, **Then** 明确提示"已完成 2 轮"。
4. **Given** 学生浏览完本轮最后一个单词但**当天未完成当日测验**, **When** 查看首页, **Then** 已完成轮数**不增加**（仍为上一数值），页面提示需完成当日测验才计入该轮。
5. **Given** 学生处于某一轮进行中, **When** 查看学习页, **Then** 显示当前轮次的推进程度（本轮已学单词数 / 词库总数）。
6. **Given** 学生查看首页, **When** 页面渲染, **Then** 以**加大字体**展示坚持建议"建议初中会考前每天坚持学习，至少完成 10 轮"。
7. **Given** 学生重新登录或换设备登录, **When** 查看轮次信息, **Then** 轮数与当前轮进度与之前完全一致。
8. **Given** 学生长期未学后回来继续当前轮, **When** 查看轮次信息, **Then** 已完成轮数不变，当前轮进度保留中断时的值。

---

### User Story 3 - 新一轮沿用既有的学习与测验规则 (Priority: P2)

新一轮中的每一天与首轮完全一致：按每日目标分配当日单词 → 逐个浏览标记 → 全部浏览完成后解锁当日测验 → 测验答错进入错题本与错题库；每日目标修改等既有规则在新一轮中同样生效。

**Why this priority**: 保证循环学习与既有流程不冲突，学生不需要重新适应新的操作方式。

**Independent Test**: 在新一轮中改每日目标 → 完成浏览 → 解锁测验 → 答错进入错题本；单独交付即验证"新一轮与首轮同规则"。

**Acceptance Scenarios**:

1. **Given** 新一轮中的某一天, **When** 学生完成当日全部单词浏览, **Then** 当日测验解锁（与首轮同一规则）。
2. **Given** 新一轮测验中答错某词, **When** 测验提交, **Then** 该词按既有规则进入错题本与错题库（规则不变）。
3. **Given** 学生在当日尚未浏览任何单词时修改每日目标, **When** 再次进入学习页, **Then** 当日集合按新目标重新分配（既有规则在新一轮中同样生效）。
4. **Given** 学生在新一轮中查看错题本 / 错题库, **When** 打开, **Then** 内容与轮次切换无关，仍按既有错题规则维护。

---

### User Story 4 - 轮次推进不丢失历史 (Priority: P2)

轮次推进只影响"接下来学哪些词"，不清除任何历史数据：以往每一天的学习记录、测验结果、错题本与错题库内容，以及（后续）学习日历总结中的历史明细，在跨轮之后仍然完整可查。

**Why this priority**: 循环学习若清空历史，等于抹掉学生的成长轨迹，也会破坏学习日历总结的回溯价值。

**Independent Test**: 学完一轮 → 跨入新一轮 → 回看历史日期的学习与测验记录、错题本 / 错题库 → 数据与跨轮前一致；单独交付即验证"循环不清历史"。

**Acceptance Scenarios**:

1. **Given** 学生已完成一轮并进入新一轮, **When** 查看错题本与错题库, **Then** 内容与此前完全一致，不因换轮而清空或减少。
2. **Given** 学生已完成一轮并进入新一轮, **When** 回看历史日期的当日学习与测验记录, **Then** 数据仍然完整可查。
3. **Given** 学生已完成一轮并进入新一轮, **When** 查看学习日历总结（功能 002）的历史日期, **Then** 历史日期的着色与明细不受轮次切换影响。

---

### Edge Cases

- **轮末日未完成测验**：学生浏览完本轮最后一个单词但当天未做当日测验 —— 该轮不计完成；为避免"卡住无法补做"，次日开始时该轮按补记规则处理（见 Assumptions）。
- 跨轮过渡日：当前轮只剩少量单词（少于每日目标）时，当日只分配剩余单词，不从新一轮提前借词凑满（与既有"剩余不足即少分配"一致）。
- 词库内容更新（新增或删除单词）后轮次如何计算？（见 Assumptions：已完成的轮次不追溯重算；新一轮按更新后的词库覆盖）
- 学生长期中断（数月）后回来：继续当前轮剩余部分，不重置轮次与进度。
- 多设备同时学习同一账号：轮次与进度按账号统一推进，不出现两份并行轮次。
- 数据缺失 / 接口异常：页面给出可理解的提示，不出现空白或英文错误堆栈。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When the word library has been fully learned, System MUST automatically start a new round instead of leaving the student with no words to learn.
- **FR-002**: System MUST allocate each day's words in the current round from words that have not yet appeared in that round.
- **FR-003**: Within a single round, System MUST cover every word in the library exactly once (no duplicates before the round completes, no omissions).
- **FR-004**: **轮完成判定** — System MUST count a round as completed only when both conditions are met: the last word of the current round has been viewed, **and** that day's daily quiz has been completed; viewing alone MUST NOT increment the completed-round count.
- **FR-005**: System MUST display the number of completed rounds to the student (e.g. "已完成 2 轮"), including the zero-round state before the first pass finishes.
- **FR-006**: System MUST display the current round's progress (words learned in the current round vs. total words in the library).
- **FR-007**: System MUST apply the existing learning and quiz rules unchanged within every round: browse all words of the day → unlock that day's quiz → wrong answers flow into 错题本 and 错题库.
- **FR-008**: System MUST NOT clear or alter historical data when a round advances: past daily records, quiz results, 错题本, 错题库, and daily summaries used by 学习日历总结 MUST remain intact.
- **FR-009**: System MUST NOT mix rounds within a single day's set: when the current round has fewer words left than the daily goal, the day MUST be allocated the remaining words only, and the next round MUST start on a subsequent day.
- **FR-010**: System MUST maintain a single round and progress per account, consistent across re-login and multiple devices.
- **FR-011**: Round and progress data MUST be visible only to the owning account and MUST NOT be shared or synced to any third party.
- **FR-012**: **新一轮取词顺序** — System MUST order words within every round by the library's original order, so that each round starts from the first word of the library and proceeds in the same sequence as the first pass.
- **FR-013**: **轮次信息展示** — System MUST display the completed-round count on the **home page**, together with the encouragement message "建议初中会考前每天坚持学习，至少完成 10 轮" rendered in **enlarged font**（**不小于正文的 1.5 倍 / Tailwind `text-lg` 及以上**，以页面正文为基准可客观比对）, and MUST display the current round's progress (learned / total) on the **study page**.
- **FR-015**: **轮末待测验提示** — When the last word of the current round has been viewed but that day's quiz is not yet completed, System MUST tell the student on both the home page and the study page that this round will not count until today's quiz is completed.
- **FR-014**: **轮末补记** — When the last word of a round has been viewed but that day's quiz was never completed, System MUST settle the round on the following day by recording it as completed, so that the student is never stuck with a round that cannot be finished. The settlement MUST happen on **every entry point that reads the current round or its progress**（首页概览、学习页分配，以及刷新 / 重新登录 / 跨设备请求）, so that no screen can show a stale, un-settled round count（SC-006）.

### Key Entities *(include if feature involves data)*

- **学习轮次（Study Round）**: 某账号对词库的一次完整遍历——轮序号（第几轮）、开始日期、完成日期（未完成为空）、本轮已学单词数 / 词库总数、是否已完成。同一账号同一时刻只有一个"进行中"的轮次；完成条件为 FR-004（浏览完 + 当日测验完成）。
- **本轮取词游标**（实现方式由方案决定）: 标记当前轮"下一个待分配单词"的位置，按词库原顺序单调推进，用于保证"每轮每词恰好一次"并派生本轮进度；**不建"单词—轮次"归属明细表**（需求不要求查询"某词在哪一轮学过"）。
- **已完成轮数**: 由已完成的轮次数量派生，长期保留、不因中断或换设备而变化。
- **既有数据来源（复用，不推翻）**: 每日学习集合与浏览标记、今日测验结果、错题本、错题库、每日目标——本功能只改变"取词范围与轮次统计"，不改变这些功能的既有规则。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 词库学完后，学生在下一个学习日仍能获得待学习单词（不再出现"今日暂无待学习单词"的空状态）。
- **SC-002**: 词库学完后，学生仍能正常解锁并完成今日测验（不再出现测验永久无法开始的情况）。
- **SC-003**: 轮次数字 100% 与实际完成遍数一致（抽查跨轮场景：完成第 2 遍并做完当日测验即显示"已完成 2 轮"；仅浏览未测验时不增加）。
- **SC-004**: 每轮覆盖率 100% 且无重复：一轮结束时词库中每个单词恰好被学习一次。
- **SC-005**: 跨轮后历史数据 100% 保留：历史日期记录、错题本、错题库与日历总结明细均不变。
- **SC-006**: 轮次与当前轮进度在刷新、重新登录、跨设备后 100% 一致。
- **SC-007**: 学生进入首页即可看到"已完成几轮"与坚持建议，进入学习页即可看到当前轮进度；验收口径为**轮次信息随既有首页 / 学习页接口一并返回**（不新增请求、不新增页面），接口 p95 < 300ms（与既有性能目标一致）。
- **SC-008**: 轮末"只浏览未测验"的状态 100% 被提示到：首页与学习页均显示"完成今日测验才计入本轮"，且此时已完成轮数不增加（FR-015）。

## Assumptions

- 词库规模以实际内置词表为准（当前 2096 词）；轮次统计以"按词库原顺序覆盖完当前词库全部单词"为一轮。
- **轮末日未完成测验的兜底**（FR-014）：当日测验机会随该日结束而不再可补答，因此次日开始时该轮按"已完成"补记，避免学生卡在永远无法收尾的一轮里；补记在**轮次读取的统一入口**触发（首页与学习页走同一路径，避免某一屏读到补记前的旧轮数）；补记只影响轮次计数，不为该日伪造测验成绩。
- 跨轮过渡日按剩余数量分配（不足每日目标即少分配），不从新一轮提前借词凑满，与既有行为保持一致。
- 词库内容若后续更新（新增 / 删除单词），已完成的轮次不追溯重算；新一轮按更新后的词库覆盖。
- 沿用既有服务端统一的「当日」口径与时区，与每日学习集合、今日测验一致。
- 首页坚持建议文案（"建议初中会考前每天坚持学习，至少完成 10 轮"）为本版固定文案；本版不因是否达到 10 轮而改变提示内容或提供达标奖励。
- 本功能不改变错题本 / 错题库的任何既有进出规则，也不改变每日目标的既有生效规则。
- **本版不考虑历史账号**：不做已有账号的数据迁移、学习进度继承或轮次回填；已有学习历史的账号在本版范围内的行为不做定义与保证。本功能保证的"跨轮不清除历史数据"（FR-008 / US4）与"历史账号迁移"是两件事，后者不在范围内。
- 本功能与「学习日历总结」（002）共享每日学习数据：轮次推进不影响 002 的历史明细。
