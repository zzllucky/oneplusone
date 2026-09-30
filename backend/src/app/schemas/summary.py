"""学习日历总结响应模型（只读聚合，不含任何在线时长字段）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class PracticeStat(BaseModel):
    """专项练习 / 测验的通用四项数字。"""

    rounds: int = 0
    answered: int = 0
    correct: int = 0
    wrong: int = 0


class QuizStat(PracticeStat):
    """今日测验：在四项数字之外，单日明细还要给出「是否完成」。"""

    completed: bool = False


class CalendarDay(BaseModel):
    """月历中的一天。"""

    date: str
    # gray = 无记录；light = 有当日集合但无学习行为；deep = 有学习行为
    level: Literal["gray", "light", "deep"]
    # 深绿分档：0 = 非深绿；1 = 1–9 词；2 = 10–29 词；3 = ≥30 词
    shade: int = 0
    learned_count: int = 0


class MonthTotal(BaseModel):
    """月度汇总（不含在线时长）。"""

    learned_words: int = 0
    quiz: PracticeStat = PracticeStat()
    review_practice: PracticeStat = PracticeStat()
    archive_practice: PracticeStat = PracticeStat()
    active_days: int = 0


class MonthSummary(BaseModel):
    month: str
    today: str
    days: list[CalendarDay]
    month_total: MonthTotal
    streak_days: int = 0


class DaySummary(BaseModel):
    """单日四项明细（不含在线时长）。"""

    date: str
    has_record: bool = False
    learned_count: int = 0
    quiz: QuizStat = QuizStat()
    review_practice: PracticeStat = PracticeStat()
    archive_practice: PracticeStat = PracticeStat()
