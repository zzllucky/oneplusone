# Feature Specification: 学习日历总结

**Feature Branch**: `002-study-calendar-summary`

**Created**: 2026-09-29

**Status**: Ready for Implementation

**变更记录（2026-09-30）**: 经确认**移除「在线时长」**，涉及原 FR-007 / FR-017 / FR-020 / FR-024、US2 验收 2 与 8、SC-005 及相应 Edge Cases：本功能**不采集任何在线时长数据**，相关字段、上报接口与展示全部取消。三级着色的「浅绿」改以**既有数据**判定（当天已生成每日学习集合 = 打开过首页或学习页，但无任何学习行为），**不新增任何个人信息字段**，因此不触发章程「附加约束 · 领域合规 第 6 条」的前置审查。

**Input**: User description: "新增一个总结的功能 里面的功能是个日历，有登陆过就变成绿色 没登陆过的就是灰色 绿色的点击上去显示点击当天的一个情况 比如学习了多少个单词，在线多少分钟，测验对了多少个单词错了多少个单词 错题本专项练习的情况 错题库专项练习的情况"

## Clarifications

### Session 2026-09-29

- Q: 日历上「绿色」怎么判定？ → A: **分深浅两级** —— 登录但没学 = 浅绿，有学习行为 = 深绿，并按当天学习量分档加深
- Q: 「在线多少分钟」按哪种口径统计？ → A: ~~前台活跃累计（页面在前台才计时、分钟级累加）~~ **2026-09-30 变更：本指标取消，不再采集任何在线时长**
- Q: 总结页除日历和单日明细，还要什么？ → A: **加当月总计 + 连续天数** —— 再提供当月总学习词数、总测验数等月度汇总，以及连续学习天数（不含在线时长）

### Session 2026-09-30

- Q: 在线时长还要不要做？ → A: **不做，从 002 中整体移除**（不采集、不存储、不展示）；其余功能照常开发。
- Q: 移除时长后「浅绿」靠什么判定？ → A: 沿用**既有数据** —— 当天已生成每日学习集合（打开首页 / 学习页即产生）但无任何学习行为 = 浅绿；无该记录 = 灰色。**不新增任何采集字段**。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 学习日历总览（哪天学过、学了多少一眼看到） (Priority: P1)

学生在站内新增的「总结」页看到一个月历，日期按当天活动情况分三级着色：**灰色** = 当天无任何使用记录；**浅绿** = 当天打开过首页或学习页（已生成当日学习集合）但没有任何学习行为；**深绿** = 当天有学习行为，且颜色深浅随当天学习量递增。默认展示当前月份，可向前 / 向后切换月份查看历史。「今天」有明确标识。

**Why this priority**: 这是本功能的主入口与核心视觉，没有日历就无法选择日期，后面所有明细都无从查看。

**Independent Test**: 登录 → 进入「总结」页 → 看到当月日历，学过单词的日子为深绿、只登录未学的为浅绿、其余为灰色 → 点击上月 / 下月可查看其他月份；单独交付即构成可用的"学习打卡视图"。

**Acceptance Scenarios**:

1. **Given** 已登录用户进入「总结」页, **When** 页面加载, **Then** 默认显示**当前月份**的完整日历，每个日期按当天活动情况显示为灰色 / 浅绿 / 深绿。
2. **Given** 用户某天打开过首页 / 学习页但没学单词、没做测验与练习, **When** 查看该日期, **Then** 显示为**浅绿**，点击后明确显示当天没有学习行为（各项数据为 0 或"未进行"）。
3. **Given** 用户某天学习了单词, **When** 查看该日期, **Then** 显示为**深绿**，且深浅随当天学习单词数递增（学得越多颜色越深）。
4. **Given** 用户在日历上切换月份, **When** 点击上一个月 / 下一个月, **Then** 显示对应月份的日历，并按该月实际活动情况着色。
5. **Given** 当前日期, **When** 日历渲染, **Then** 「今天」与其他日期有可辨识的区分标识。
6. **Given** 用户重新登录或在另一台设备登录同一账号, **When** 查看日历, **Then** 着色结果与之前一致（历史活动不会因换日、刷新、重新登录而丢失）。

---

### User Story 2 - 查看某天的学习明细 (Priority: P1)

学生点击日历上的**浅绿或深绿日期**，看到这一天的完整情况：**学习单词数**、**今日测验答对数与答错数**、**错题本专项练习情况**、**错题库专项练习情况**；当天没有某项活动时，该项显示为零或"未进行"，而不是报错或空白。

**Why this priority**: 日历只解决"哪天学过"，明细才回答"那天学得怎么样"，是用户明确点名要的数据。

**Independent Test**: 在有活动的某天完成学习 + 今日测验 + 两类专项练习 → 进入总结页 → 点击该日期 → 四项数据全部显示且与实际行为一致；单独交付即可作为"单日学习报告"。

**Acceptance Scenarios**:

1. **Given** 某有活动日期当天浏览了 N 个单词, **When** 点击该日期, **Then** 明细显示"学习单词数 = N"，与当天实际标记的已浏览数量一致。
2. **Given** 某有活动日期当天完成了今日测验, **When** 点击该日期, **Then** 明细分别显示测验**答对单词数**与**答错单词数**（以及由此得出的正确率），与测验结果一致。
3. **Given** 某有活动日期当天做过错题本专项练习, **When** 点击该日期, **Then** 明细显示该练习情况：完成轮数、答题数、答对数、答错数。
4. **Given** 某有活动日期当天做过错题库专项练习, **When** 点击该日期, **Then** 明细显示该练习情况：完成轮数、答题数、答对数、答错数。
5. **Given** 某日期当天只打开过页面、未产生任何学习 / 测验 / 练习, **When** 点击该浅绿日期, **Then** 明细中各项均显示为零或"未进行"，并明确提示当天没有学习行为。
6. **Given** 同一天进行了多轮专项练习, **When** 点击该日期, **Then** 各项数据为当天全部轮次的**汇总值**，不因多轮而互相覆盖。

---

### User Story 3 - 灰色日期与未来日期不可查看 (Priority: P2)

学生点击**灰色日期**（当天无任何活动）或**未来日期**时，不会被误导认为有数据：要么不可点击，要么点击后明确提示"当天没有学习记录"。

**Why this priority**: 避免用户在无数据日期上重复点击却得不到反馈，是主流程的边界体验。

**Independent Test**: 进入总结页 → 点击一个从未使用过的过去日期与一个未来日期 → 得到明确"无记录"反馈而非空白或报错；单独交付即可闭环边界体验。

**Acceptance Scenarios**:

1. **Given** 某过去日期当天没有任何活动, **When** 用户点击该灰色日期, **Then** 系统明确提示当天没有学习记录（不显示空白面板，也不报错）。
2. **Given** 当前月份之后的日期, **When** 用户点击, **Then** 不展示明细数据并给出相应提示。
3. **Given** 注册之前的日期, **When** 用户查看, **Then** 显示为无活动的灰色状态。

---

### User Story 4 - 当月总计与连续学习天数 (Priority: P2)

学生在「总结」页除日历外，还能直接看到**当月汇总**：当月总学习单词数、今日测验总题数与答对 / 答错数、两类专项练习的总轮数与答题 / 答对 / 答错数、当月有活动的天数；同时看到**连续学习天数**（连续有学习行为的天数），用于自我激励。切换月份时，当月总计随所查看月份变化。

**Why this priority**: 单日明细是点状数据，月度汇总与连续天数给出"这一个月坚持得怎么样"的整体反馈，是总结页的主要激励价值。

**Independent Test**: 在有跨多天数据的月份进入总结页 → 页面顶部显示当月总计与连续天数 → 切到另一月份总计随之变化 → 数字与逐日明细加总一致；单独交付即构成"月度成绩单"。

**Acceptance Scenarios**:

1. **Given** 用户在当月多天产生过学习数据, **When** 进入总结页, **Then** 显示当月总学习单词数、测验总题数与答对 / 答错数、两类专项练习汇总，以及当月有活动天数。
2. **Given** 用户切换查看的月份, **When** 点击上一个月 / 下一个月, **Then** 月度总计切换为该月份的数据。
3. **Given** 用户连续多天有学习行为, **When** 进入总结页, **Then** 显示与实际情况一致的连续学习天数。
4. **Given** 用户今天尚未学习但昨天及之前连续学习过, **When** 进入总结页, **Then** 连续天数按最近一次连续区间显示，**不因当天还没学而显示为 0**。
5. **Given** 用户连续区间中断一天后再学习, **When** 进入总结页, **Then** 连续天数从新的起点重新计算。
6. **Given** 当月无任何活动, **When** 进入总结页, **Then** 月度总计各项显示为零或"未进行"，连续天数显示为 0。

---

### User Story 5 - 历史长期可回溯 (Priority: P3)

学生的每日汇总数据长期保留：换日、刷新、重新登录、更换设备后，过去任意有活动日期的明细都能再次查看。

**Why this priority**: 总结的价值在于纵向对比（"我这周/这个月学了多少"），数据不可回溯则该功能失去意义。

**Independent Test**: 在多天产生数据 → 隔日重新登录 → 逐月回看 → 每个历史有活动日期仍可点开且数据不变；单独交付即验证持久化。

**Acceptance Scenarios**:

1. **Given** 用户在过去某天产生了学习数据, **When** 隔日重新登录并回看该日期, **Then** 明细数据与当天一致，不因日期切换而清空。
2. **Given** 用户在同一账号下更换设备登录, **When** 查看历史日期, **Then** 看到的日历着色与明细数据完全一致。
3. **Given** 用户某天在多个时段使用（例如上午与晚上）, **When** 查看该日期, **Then** 当天数据合并为一份汇总呈现。

---

### Edge Cases

- 用户在 23:5x 开始学习并跨过零点：该次活动如何归属日期？（见 Assumptions：按服务端统一"当日"口径归属，以行为发生时刻所属日期为准）
- 当天多次打开 / 多设备同时登录：学习、测验与练习数据按天合并汇总，不重复计数。
- 当天只做了专项练习、没有学习新单词：学习单词数为 0，但当天仍为深绿并显示专项练习明细。
- 注册当天（或任意一天）只打开页面、未产生任何学习行为：显示为浅绿，明细各项为 0 或"未进行"。
- 数据缺失 / 接口异常：页面给出可理解的提示，不出现空白或英文错误堆栈。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a "总结" page accessible to logged-in students, whose primary view is a month calendar.
- **FR-002**: System MUST render each date in one of three states — **gray** / **light green** / **deep green**（三态的判定与分档规则以 FR-019 为准）。
- **FR-003**: System MUST default the calendar to the current month and allow navigating to previous and next months.
- **FR-004**: System MUST mark the current day distinctly from other dates.
- **FR-005**: Users MUST be able to click a light-green or deep-green date to open that day's detail summary.
- **FR-006**: The daily detail MUST show the number of words learned (marked as viewed) that day.
- **FR-008**: The daily detail MUST show the daily quiz result: number of words answered correctly and number answered incorrectly.
- **FR-009**: The daily detail MUST show the 错题本 (review) practice result: rounds completed, questions answered, correct count, wrong count.
- **FR-010**: The daily detail MUST show the 错题库 (archive) practice result: rounds completed, questions answered, correct count, wrong count.
- **FR-011**: When a day has no data for one of the four metrics (学习单词数、今日测验、错题本专项、错题库专项), System MUST display zero or an explicit "未进行" state instead of an error or blank.
- **FR-012**: When a day has multiple practice rounds, System MUST aggregate all rounds of that day into the daily figures.
- **FR-013**: System MUST assign all activity to a date using the product's existing single server-side "当日" definition, so that activity spanning midnight is attributed to the date on which it occurred.
- **FR-014**: System MUST persist daily summaries permanently: they survive date changes, page refresh, re-login and access from another device.
- **FR-015**: System MUST treat dates with no activity (including pre-registration and future dates) as having no viewable detail: clicking them yields an explicit "no record" indication.
- **FR-016**: Daily summary data MUST be visible only to the owning account.
- **FR-018**: System MUST NOT share, export, or sync the collected summary data to any third party; it stays in the product's own storage.
- **FR-019**: **分级着色规则** — System MUST color a date **gray** when there is no usage record for that day, **light green** when the daily study set exists for that day (the student opened the home or study page) but no learning activity was produced (no words learned, no quiz, no practice), and **deep green** when the student produced at least one learning activity that day; deep green MUST be rendered in progressively darker shades as the number of words learned that day increases (at least three distinguishable levels).
- **FR-021**: **页面范围** — The 总结 page MUST provide, in addition to the calendar and the single-day detail, a **monthly total panel** and a **consecutive learning days** indicator.
- **FR-022**: **月度汇总字段** — The monthly total MUST show, for the month being viewed: total words learned, daily quiz totals (questions answered, correct, wrong), 错题本 practice totals (rounds, questions answered, correct, wrong), 错题库 practice totals (same fields), and the number of days with activity（**不含在线时长**）。
- **FR-023**: **连续学习天数口径** — System MUST count consecutive days with learning activity (deep-green days); when the current day has no learning activity yet, the displayed streak MUST reflect the most recent consecutive run instead of resetting to zero.

### Key Entities *(include if feature involves data)*

- **每日学习汇总（Daily Summary）**: 某账号在某一日的汇总记录——当天活动等级（无记录 / 仅打开 / 有学习）、学习单词数、今日测验答对 / 答错数、错题本专项练习（轮数 / 答题数 / 答对数 / 答错数）、错题库专项练习（同前）。同一账号同一日仅一份，长期保留。**不含在线时长**。
- **月度汇总（Monthly Total）**: 由某月各日汇总加总得出的月度视图，不单独存储口径之外的信息；切换月份时随之变化。
- **既有数据来源（只读复用）**: 账号、每日学习集合与浏览标记、今日测验结果、错题本专项练习结果、错题库专项练习结果——本功能只汇总展示，不改变这些功能的既有规则；**浅绿判定直接复用"当日学习集合是否存在"这一既有痕迹，不新增任何采集字段**。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 进入「总结」页后，学生在 3 秒内看到当月日历，且能立即分辨出哪些日期有学习活动、哪些只是登录过。
- **SC-002**: 点击任一浅绿 / 深绿日期后，学生在 1 秒内看到该日四项数据（学习单词数、测验对 / 错数、错题本专项、错题库专项）。
- **SC-003**: 任意有学习行为的日期 100% 显示为深绿，且其明细数字与该日实际行为一致（抽查多日无偏差）。
- **SC-004**: 日历着色与明细在刷新、重新登录、跨设备登录后 100% 保持一致。
- **SC-006**: 学生可在 3 次点击内回看任意历史月份中某一天的完整明细。
- **SC-007**: 总结页数据仅本人可见，他人账号无法查看；数据不出站、不共享第三方（合规可核查）。
- **SC-008**: 月度总计各项数字 100% 等于该月各日明细之和（抽查月份无偏差）。
- **SC-009**: 连续学习天数与实际连续有学习行为的天数一致，且当天未学习时不显示为 0（中断一天后才重新计数）。

## Assumptions

- 学生具备稳定网络访问；本功能只汇总**已成功写入的既有数据**（学习、测验、专项练习），不新增任何上报、不做事后补算。
- 「当日」沿用产品既有的服务端统一口径（与每日学习集合、今日测验一致），跨零点活动按行为发生时刻归属到各自日期。
- 深绿深浅分档按当天学习单词数划分（例如 1–9 / 10–29 / ≥30 词三档），具体阈值在方案阶段确认并以可辨识为原则。
- 本功能只做汇总与展示，不改变既有学习、测验、错题本 / 错题库的既有规则。
- 历史数据默认长期保留，本版不提供数据导出、删除与分享能力。
- **合规结论（2026-09-30）**：原拟新增的"在线时长"已整体取消。本功能**不采集、不存储、不展示任何在线时长数据**，也不采集页面内容、点击流或任何可用于画像的行为数据；浅绿的"当天是否打开过"直接复用既有的每日学习集合痕迹，**未新增任何未成年人个人信息字段**，因此**不触发**章程「附加约束 · 领域合规 第 6 条」的前置审查；本条即审查结论，记录于本功能目录下。
