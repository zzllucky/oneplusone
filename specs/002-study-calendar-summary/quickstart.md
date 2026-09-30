# Quickstart: 学习日历总结

**Feature**: `002-study-calendar-summary` | **Date**: 2026-09-30

端到端验证指南（对应 `contracts/api.md` 与 `data-model.md`）。

## 前置

1. 本地可启动后端（默认 `http://localhost:8000`）与前端；
2. 已执行迁移到 head（含本次新增的 `005_summary_query_indexes`）：

   ```bash
   cd backend && alembic upgrade head && alembic current   # 期望：005 (head)
   ```

3. 既有功能（001 学习 / 测验 / 错题本 / 错题库、003 轮次）正常，因为本功能**只读聚合**它们产生的数据。

> 造历史数据：手工"跨多天学习"不现实，使用本地造数脚本（不入 Docker 镜像）生成最近 N 天的历史行为（**请在本地测试库或专用测试账号上执行**；脚本只增不删，勿对真实学习数据运行）：
>
> ```bash
> cd backend && python scripts/seed_summary_history.py --user stu01 --days 30
> ```
>
> 脚本只**新增**既有的学习集合、浏览标记、测验与专项练习记录，不删除任何数据；可重复执行（幂等按日期覆盖）。

## 场景 A —— 日历三级着色（US1 / FR-019）

1. 用造数脚本造出三类日期：某天学了 18 词、某天只打开过页面、某天完全没打开。
2. 打开「总结」页（或 `GET /api/summary/month`）。
3. **预期**：学过的那天为深绿（`shade` 2）、只打开过的那天为浅绿、没打开过的为灰色；「今天」有独立标识；默认显示当前月。

## 场景 B —— 单日明细四项（US2 / FR-006 / FR-008 / FR-009 / FR-010）

1. 在造数出的某天（有学习 + 完成今日测验 + 两类专项练习各 1 轮）点击该日期。
2. **预期**：明细显示学习单词数、今日测验答对 / 答错（含正确率）、错题本专项（轮数 / 答题 / 对 / 错）、错题库专项（同前），与实际行为一致；**不出现"在线时长"**。

## 场景 C —— 灰色日与未来日期（US3 / FR-015）

1. 点击一个从未使用过的过去日期，再点击一个本月之后的日期。
2. **预期**：均给出"当天没有学习记录"提示（`has_record=false`），不出现空白面板或报错。

## 场景 D —— 月度汇总与连续天数（US4 / FR-022 / FR-023）

1. 造出连续多天有学习行为（例如最近 5 天），进入总结页。
2. **预期**：月度总学习词数 = 各日明细之和；今日测验与两类专项的汇总与逐日加总一致；有活动天数正确；「连续学习 5 天」。
3. 今天还没学就打开页面 → **预期**：连续天数仍显示 5（不归 0）；中断一天后再学 → 从新起点计数。
4. 切到一个完全没有活动的月份 → **预期**：月度总计各项为 0 / "未进行"，连续天数为 0。

## 场景 E —— 跨月切换（US1 验收 4 / FR-003）

1. 点击上一个月 / 下一个月。
2. **预期**：日历与月度总计随之切换为该月数据；未来月份全灰。

## 场景 F —— 历史回溯与跨设备一致（US5 / FR-014 / SC-004）

1. 造数出上个月的若干天数据 → 切到上个月 → 逐日点开。
2. 刷新页面、退出重新登录、换浏览器（或换设备）登录同一账号，重复第 1 步。
3. **预期**：着色、明细、月度总计、连续天数**完全一致**；历史日期不因换日 / 刷新 / 重新登录而丢失。

## 自动化等价覆盖（无需手工）

```bash
cd backend && pytest -q -m "unit or contract or integration" -k summary
```

| 场景 | 测试载体（实施阶段创建） |
|---|---|
| A 着色三级与分档 | `tests/unit/test_summary_service.py`（level / shade 规则） |
| B 明细四项口径 | `tests/unit/test_summary_service.py` + `tests/contract/test_summary_contract.py` |
| C 无记录日期 | `tests/contract/test_summary_contract.py`（`has_record=false`，非 404） |
| D 月度汇总与连续天数 | `tests/unit/test_summary_service.py`（含"当天未学不归零"） |
| E 跨月与参数校验 | `tests/contract/test_summary_contract.py`（`invalid_month` / `invalid_date`） |
| F 跨设备一致与历史保留 | `tests/integration/test_summary_flow.py`（真实 SQLite + HTTP，禁用 mock） |

## 回归项

- 001 既有功能不受影响：`pytest -q` 全绿（新增端点，不改既有端点）。
- 003 的 US4 验收 3「学习日历总结的历史日期着色」：本功能交付后该项应可闭环，请回 `specs/003-library-cycle-rounds/tasks.md` 的记录中标注已回归。
- 索引生效确认：`pytest -q tests/unit/test_summary_indexes.py`（断言迁移 `005` 的 3 个索引真实存在于 `sqlite_master`，避免 003 那个"索引静默丢失"的坑重演）。
