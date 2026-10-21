# Requirements Quality Checklist: 初中英语语法学习（大纲 · 学卡 · 练习）

**Purpose**: 对 `spec.md` 的需求质量做"英语单元测试" —— 检查需求的完整性、清晰性、一致性、可测性、场景与边界覆盖、非功能要求与假设，供作者在提交评审前自查。
**Created**: 2026-10-19
**Feature**: [spec.md](../spec.md)

**Note**: 本清单由 `/speckit.checklist` 基于功能上下文与需求文档生成，检查对象是**需求本身写得好不好**，不是实现是否完成。
**Review Ownership**: 本清单为评审者拥有的需求质量评审制品；仅当评审者判定该条需求质量准则已满足时才标记 `[x]`。
**Marker Semantics**: `[x]` 表示该需求质量准则已通过评审，**不表示**实现工作已完成。

<!-- 维度说明：本轮聚焦「需求质量总检」，深度为「标准」，受众为「作者自查」。 -->

## Requirement Completeness

- [X] CHK001 Are 四条用户故事（US1 大纲 / US2 学卡 / US3 练习 / US4 错题回链）都给出了可独立测试的入口与独立价值说明？ [Completeness, Spec §US1–US4]
- [X] CHK002 Are 大纲页所需的全部展示要素（分组依据、深度标签、状态、汇总计数）都被列为需求？ [Completeness, Spec §FR-001–FR-003]
- [X] CHK003 Are 三种卡面（规则型 / 对比型 / 速记型）各自必须呈现的内容项都被逐项列出？ [Completeness, Spec §FR-004]
- [X] CHK004 Are 学后检测与题库练习在"判分后必须返回哪些内容"上都定义完整（正确项、解析、错因）？ [Completeness, Spec §FR-005/FR-009]
- [X] CHK005 Are 语法错题本列表需要展示的每个字段都被明确列出？ [Completeness, Spec §FR-014]
- [X] CHK006 Are "只看不测""未全对"这类非完成路径的结果状态被显式定义？ [Completeness, Spec §US2·AC5/AC6]
- [X] CHK007 Are 语法与单词两个板块"互不影响"的具体方面被逐项列举，而非一句概括？ [Completeness, Spec §FR-020]

## Requirement Clarity

- [X] CHK008 Is "掌握"的判定条件唯一且无歧义（唯一触发路径、全对才成立）？ [Clarity, Spec §FR-006]
- [X] CHK009 Is "学习中"状态对所有触发情形做了穷举定义（已学未测、测了未全对）？ [Clarity, Spec §FR-006]
- [X] CHK010 Is 错题移除的"连续答对阈值"给出具体数值，而非模糊表述？ [Clarity, Spec §FR-013]
- [X] CHK011 Is "即时判分"界定了响应时机与判分响应必须包含的内容清单？ [Clarity, Spec §FR-009]
- [X] CHK012 Is "L1 识别 / L2 变形 / L3 陷阱"三层的含义定义到可直接实现的程度？ [Clarity, Spec §FR-008]
- [X] CHK013 Is 错题回链的粒度（题目 → 知识点）在需求中明确，使实现无需再猜测？ [Clarity, Spec §FR-012]
- [X] CHK014 Is 大纲汇总计数"已掌握 / 全部"的统计口径被明确（以学习卡为单位还是以考点为单位）？ [Clarity, Spec §FR-003]

## Requirement Consistency

- [X] CHK015 Are FR-006（掌握只由学后检测判定）与 FR-012（检测答错同样进错题本）之间没有冲突？ [Consistency, Spec §FR-006/FR-012]
- [X] CHK016 Are FR-015（一轮内重复作答以首次为准）与 FR-016（已结束轮次拒绝作答）对同一提交情形的判定一致？ [Consistency, Spec §FR-015/FR-016]
- [X] CHK017 Are 用户故事中对掌握与错题规则的描述与 Functional Requirements 的表述一致？ [Consistency, Spec §US2/US4 vs FR-006/FR-012/FR-013]
- [X] CHK018 Are Edge Cases 中列出的情形与对应 FR 的判定一致、无相互矛盾？ [Consistency, Spec §Edge Cases]
- [X] CHK019 Are Clarifications 中逐条确认的结论都能在 FR 中找到对应条款？ [Consistency, Spec §Clarifications]

## Acceptance Criteria Quality

- [X] CHK020 Can SC-001 的"3 次点击内"被客观计数（起点、终点与一次点击的定义明确）？ [Measurability, Spec §SC-001]
- [X] CHK021 Can SC-002 的"100% 一致"给出可验证的比对口径（与哪份数据比对）？ [Measurability, Spec §SC-002]
- [X] CHK022 Is SC-003 的响应指标明确了测量环境、范围与统计量（p95）？ [Measurability, Spec §SC-003]
- [X] CHK023 Is SC-005（不影响单词模块）给出可判定的回归基线？ [Measurability, Spec §SC-005]
- [X] CHK024 Is SC-006 的"完整可用"在三种视口下给出可判定标准（如无横向滚动、无溢出）？ [Measurability, Spec §SC-006]

## Scenario Coverage

- [X] CHK025 Are Alternate 场景被覆盖 —— 未学知识点直接练习、只练习不做学卡、重复学习已掌握知识点？ [Coverage, Gap]
- [X] CHK026 Are Recovery 场景被覆盖 —— 练习中途退出后重入、同一知识点反复发起练习的轮次语义？ [Coverage, Spec §US3·AC4]
- [X] CHK027 Are Exception 场景被覆盖 —— 无题库题、轮次已结束、非法选项、未登录？ [Coverage, Spec §Edge Cases]
- [X] CHK028 Are 多端 / 跨设备同时学习同一知识点的并发语义被定义为需求（哪怕结论是"不保证"）？ [Coverage, Gap]

## Edge Case Coverage

- [X] CHK029 Are 空态需求被定义 —— 语法错题本为空、某知识点无题库题时的呈现与提示？ [Edge Cases, Spec §Edge Cases]
- [X] CHK030 Is 同一知识点"学后检测与练习同时进行"的互不干扰规则被明确定义？ [Edge Cases, Spec §Edge Cases]
- [X] CHK031 Is 知识点内容后续更新（合并卡、题量变化）时既有学习记录的处理口径被定义或显式排除？ [Edge Cases, Gap]

## Non-Functional Requirements

- [X] CHK032 Are 答案保护要求被定义为明确的需求（作答前不得下发哪些字段）？ [Security, Spec §FR-007]
- [X] CHK033 Are 日志要求被定义到可落地（记录哪些事件、包含哪些标识、禁止记录什么）？ [Observability, Spec §FR-022]
- [X] CHK034 Are 响应式与视口要求覆盖语法板块的全部页面而非仅大纲页？ [NFR, Spec §FR-021]
- [X] CHK035 Are 未成年人数据合规约束在需求层体现（不新增任何身份类信息、数据仅存自有服务）？ [Compliance, Spec §FR-019/Assumptions]

## Dependencies & Assumptions

- [X] CHK036 Are 全部假设（内置教研内容、无外部资源、不引入依赖、阈值集中在服务端）在 Assumptions 中列出并被 FR 覆盖？ [Assumption, Spec §Assumptions]
- [X] CHK037 Is 需求与验收标准的编号体系（FR / AC / SC）在全文一致且可被后续 tasks 与测试引用？ [Traceability, Spec §Requirements/Success Criteria]

## Notes

- 标记准则：仅当确认该条需求质量准则已满足时才勾 `[x]`；仍需澄清、修正或待评审的条目保持未勾选
- 本清单由作者自查使用；`/speckit.implement` 会读取勾选状态作为门禁，但不会修改标记
- `checklists/requirements.md` 是由 `/speckit.specify` 与 `/speckit.clarify` 维护的内置清单，与本文件生命周期不同
- 自查发现的问题直接在 spec.md 修订，无需改动本清单条目（除非需求维度本身变化）
- 2026-10-19：经用户授权，由作者逐条核对后勾选；其中 CHK007 / CHK012 / CHK014 / CHK020 / CHK021 / CHK025 / CHK026 / CHK028 / CHK031 先回改 spec.md 补齐口径（FR-003 / FR-006 / FR-008 / FR-020、US3 AC6-AC8、Edge Cases 并发与内容更新、SC-001 / SC-002）后再判定满足
- 相关文档：[spec.md](../spec.md) · [plan.md](../plan.md) · [contracts/api.md](../contracts/api.md) · [data-model.md](../data-model.md)
