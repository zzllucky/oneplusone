"""学习日历总结：按月 / 按日只读聚合（不写入、不修改、不删除任何数据）。

归日口径（research R-002 / R-003）：

- 学习单词数 → ``daily_sets.study_date``（与学习页同口径）；
- 今日测验 → ``quiz_attempts.study_date``（daily 自带该字段）；
- 两类专项练习 → ``quiz_answers.answered_at`` 换算 Asia/Shanghai 后的日期。

着色与分档（research R-004）：gray / light / deep，deep 按学习词数分 3 档。
连续天数（research R-005 / data-model）：从锚点日期往前数连续的有学习行为日。
"""

from __future__ import annotations

import datetime as dt
import logging
import re
import time
from zoneinfo import ZoneInfo

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError
from app.logging import get_logger
from app.models.daily_set import DailySet, DailySetItem
from app.models.quiz import QuizAnswer, QuizAttempt

logger = get_logger("app.services.summary_service")

_MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PRACTICE_KINDS = ("review", "archive")


def _empty_stat() -> dict:
    return {"rounds": 0, "answered": 0, "correct": 0, "wrong": 0}


def today_date() -> dt.date:
    """服务端「当日」（Asia/Shanghai）。"""
    return (
        dt.datetime.now(dt.timezone.utc).astimezone(ZoneInfo(settings.timezone)).date()
    )


def _tz_offset_minutes() -> int:
    offset = (
        dt.datetime.now(dt.timezone.utc)
        .astimezone(ZoneInfo(settings.timezone))
        .utcoffset()
    )
    return int(offset.total_seconds() // 60) if offset else 0


def _local_midnight_utc(day: dt.date) -> dt.datetime:
    """本地日期 00:00 对应的 naive UTC（用于范围扫描，可命中 answered_at 索引）。"""
    return dt.datetime.combine(day, dt.time()) - dt.timedelta(
        minutes=_tz_offset_minutes()
    )


def _local_date_expr():
    """``quiz_answers.answered_at`` → 本地日期字符串（SQLite）。"""
    return func.date(
        func.datetime(QuizAnswer.answered_at, f"{_tz_offset_minutes():+d} minutes")
    )


def _month_end(first_day: dt.date) -> dt.date:
    if first_day.month == 12:
        return dt.date(first_day.year, 12, 31)
    return dt.date(first_day.year, first_day.month + 1, 1) - dt.timedelta(days=1)


def parse_month(value: str | None) -> tuple[dt.date, dt.date]:
    """``YYYY-MM`` → (首日, 末日)；非法 → 400 invalid_month。"""
    if value is None:
        first = today_date().replace(day=1)
        return first, _month_end(first)
    if not _MONTH_PATTERN.match(value):
        raise AppError("invalid_month")
    try:
        first = dt.date(int(value[:4]), int(value[5:7]), 1)
    except ValueError:
        raise AppError("invalid_month")
    return first, _month_end(first)


def parse_date(value: str) -> dt.date:
    """``YYYY-MM-DD`` → date；非法 → 400 invalid_date。"""
    if not value or not _DATE_PATTERN.match(value):
        raise AppError("invalid_date")
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise AppError("invalid_date")


def _shade(learned_count: int) -> int:
    if learned_count >= 30:
        return 3
    if learned_count >= 10:
        return 2
    if learned_count >= 1:
        return 1
    return 0


def _learned_counts(
    db: Session, user_id: int, start: dt.date, end: dt.date
) -> dict[dt.date, int]:
    rows = db.execute(
        select(DailySet.study_date, func.count(DailySetItem.id))
        .join(DailySetItem, DailySetItem.daily_set_id == DailySet.id)
        .where(
            DailySet.user_id == user_id,
            DailySet.study_date >= start,
            DailySet.study_date <= end,
            DailySetItem.viewed_at.is_not(None),
        )
        .group_by(DailySet.study_date)
    ).all()
    return {row[0]: int(row[1]) for row in rows}


def _set_dates(
    db: Session, user_id: int, start: dt.date | None = None, end: dt.date | None = None
) -> set[dt.date]:
    """当日学习集合存在的日期（浅绿判定依据：打开过首页 / 学习页）。"""
    statement = select(DailySet.study_date).where(DailySet.user_id == user_id)
    if start is not None:
        statement = statement.where(DailySet.study_date >= start)
    if end is not None:
        statement = statement.where(DailySet.study_date <= end)
    return {row[0] for row in db.execute(statement).all()}


def _daily_quiz(
    db: Session, user_id: int, start: dt.date, end: dt.date
) -> dict[dt.date, dict]:
    rows = db.execute(
        select(
            QuizAttempt.study_date,
            func.count(QuizAttempt.id),
            func.coalesce(func.sum(QuizAttempt.total_count), 0),
            func.coalesce(func.sum(QuizAttempt.correct_count), 0),
            func.coalesce(func.sum(QuizAttempt.wrong_count), 0),
        )
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.kind == "daily",
            QuizAttempt.study_date.is_not(None),
            QuizAttempt.study_date >= start,
            QuizAttempt.study_date <= end,
            QuizAttempt.finished_at.is_not(None),
        )
        .group_by(QuizAttempt.study_date)
    ).all()
    return {
        row[0]: {
            "rounds": int(row[1]),
            "answered": int(row[2]),
            "correct": int(row[3]),
            "wrong": int(row[4]),
        }
        for row in rows
        if row[0] is not None
    }


def _practice(
    db: Session, user_id: int, kind: str, start: dt.date, end: dt.date
) -> dict[dt.date, dict]:
    """专项练习：按 ``quiz_answers.answered_at`` 的本地日期聚合（多轮累加）。"""
    local_date = _local_date_expr()
    # 前后各放宽一天，保证跨时区的边界作答不漏，同时仍能命中 answered_at 索引
    window_start = _local_midnight_utc(start - dt.timedelta(days=1))
    window_end = _local_midnight_utc(end + dt.timedelta(days=2))
    rows = db.execute(
        select(
            local_date.label("day"),
            func.count(QuizAnswer.id),
            func.coalesce(func.sum(cast(QuizAnswer.is_correct, Integer)), 0),
            func.count(func.distinct(QuizAnswer.attempt_id)),
        )
        .join(QuizAttempt, QuizAttempt.id == QuizAnswer.attempt_id)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.kind == kind,
            QuizAnswer.answered_at >= window_start,
            QuizAnswer.answered_at < window_end,
        )
        .group_by(local_date)
    ).all()
    result: dict[dt.date, dict] = {}
    for day, answered, correct, rounds in rows:
        if not day:
            continue
        parsed = dt.date.fromisoformat(day)
        result[parsed] = {
            "rounds": int(rounds),
            "answered": int(answered),
            "correct": int(correct),
            "wrong": int(answered) - int(correct),
        }
    return result


def _learning_dates(db: Session, user_id: int) -> set[dt.date]:
    """全部历史中「有学习行为」的日期（连续天数与 deep 判定的基础）。"""
    dates: set[dt.date] = set()

    rows = db.execute(
        select(DailySet.study_date)
        .join(DailySetItem, DailySetItem.daily_set_id == DailySet.id)
        .where(DailySet.user_id == user_id, DailySetItem.viewed_at.is_not(None))
        .distinct()
    ).all()
    dates |= {row[0] for row in rows}

    rows = db.execute(
        select(QuizAttempt.study_date)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.kind == "daily",
            QuizAttempt.study_date.is_not(None),
            QuizAttempt.finished_at.is_not(None),
        )
        .distinct()
    ).all()
    dates |= {row[0] for row in rows if row[0] is not None}

    local_date = _local_date_expr()
    for kind in PRACTICE_KINDS:
        rows = db.execute(
            select(local_date.label("day"))
            .join(QuizAttempt, QuizAttempt.id == QuizAnswer.attempt_id)
            .where(QuizAttempt.user_id == user_id, QuizAttempt.kind == kind)
            .group_by(local_date)
        ).all()
        dates |= {dt.date.fromisoformat(row[0]) for row in rows if row[0]}

    return dates


def _streak(dates: set[dt.date], anchor: dt.date) -> int:
    """从锚点往前数连续的有学习行为日；锚点当天未学则从昨天开始数。"""
    cursor = anchor if anchor in dates else anchor - dt.timedelta(days=1)
    if cursor not in dates:
        return 0
    count = 0
    while cursor in dates:
        count += 1
        cursor -= dt.timedelta(days=1)
    return count


def month_summary(db: Session, user_id: int, month: str | None = None) -> dict:
    started = time.perf_counter()
    first_day, last_day = parse_month(month)
    today = today_date()

    learned = _learned_counts(db, user_id, first_day, last_day)
    set_dates = _set_dates(db, user_id, first_day, last_day)
    quiz_by_day = _daily_quiz(db, user_id, first_day, last_day)
    review_by_day = _practice(db, user_id, "review", first_day, last_day)
    archive_by_day = _practice(db, user_id, "archive", first_day, last_day)

    days: list[dict] = []
    totals = {
        "learned_words": 0,
        "quiz": _empty_stat(),
        "review_practice": _empty_stat(),
        "archive_practice": _empty_stat(),
        "active_days": 0,
    }

    for offset in range((last_day - first_day).days + 1):
        day = first_day + dt.timedelta(days=offset)
        learned_count = learned.get(day, 0)
        quiz = quiz_by_day.get(day)
        review = review_by_day.get(day)
        archive = archive_by_day.get(day)
        has_learning = bool(
            learned_count > 0
            or (quiz and quiz["rounds"] > 0)
            or (review and review["answered"] > 0)
            or (archive and archive["answered"] > 0)
        )
        has_record = day in set_dates or has_learning
        if has_learning:
            level = "deep"
            shade = _shade(learned_count)
        elif has_record:
            level, shade = "light", 0
        else:
            level, shade = "gray", 0

        days.append(
            {
                "date": day.isoformat(),
                "level": level,
                "shade": shade,
                "learned_count": learned_count,
            }
        )

        totals["learned_words"] += learned_count
        for key, stat in (
            ("quiz", quiz),
            ("review_practice", review),
            ("archive_practice", archive),
        ):
            if not stat:
                continue
            totals[key]["rounds"] += stat["rounds"]
            totals[key]["answered"] += stat["answered"]
            totals[key]["correct"] += stat["correct"]
            totals[key]["wrong"] += stat["wrong"]
        if has_record:
            totals["active_days"] += 1

    anchor = min(last_day, today)
    streak_days = 0 if anchor < first_day else _streak(_learning_dates(db, user_id), anchor)

    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "summary.month user_id=%s month=%s days=%d active_days=%d elapsed_ms=%.1f",
        user_id,
        first_day.strftime("%Y-%m"),
        len(days),
        totals["active_days"],
        elapsed_ms,
    )

    return {
        "month": first_day.strftime("%Y-%m"),
        "today": today.isoformat(),
        "days": days,
        "month_total": totals,
        "streak_days": streak_days,
    }


def day_summary(db: Session, user_id: int, date: str) -> dict:
    started = time.perf_counter()
    day = parse_date(date)

    learned_count = _learned_counts(db, user_id, day, day).get(day, 0)
    quiz = _daily_quiz(db, user_id, day, day).get(day, _empty_stat())
    quiz = {**quiz, "completed": quiz["rounds"] > 0}
    review = _practice(db, user_id, "review", day, day).get(day, _empty_stat())
    archive = _practice(db, user_id, "archive", day, day).get(day, _empty_stat())
    has_record = bool(
        day in _set_dates(db, user_id, day, day)
        or learned_count > 0
        or quiz["rounds"] > 0
        or review["answered"] > 0
        or archive["answered"] > 0
    )

    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "summary.day user_id=%s date=%s has_record=%s learned=%d elapsed_ms=%.1f",
        user_id,
        day.isoformat(),
        has_record,
        learned_count,
        elapsed_ms,
    )

    return {
        "date": day.isoformat(),
        "has_record": has_record,
        "learned_count": learned_count,
        "quiz": quiz,
        "review_practice": review,
        "archive_practice": archive,
    }
