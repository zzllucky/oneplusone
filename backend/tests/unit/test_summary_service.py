"""汇总服务单元测试（T006 / T009 / T022）：聚合口径、着色分档、连续天数。

真实 SQLite + ORM 造数，禁用 mock（章程 IV）。
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from app.models.daily_set import DailySet, DailySetItem
from app.models.base import utcnow
from app.models.quiz import QuizAnswer, QuizAttempt
from app.models.word import Word
from app.services import summary_service
from tests.conftest import register

pytestmark = pytest.mark.unit

# 服务端时区 Asia/Shanghai = UTC+8（无夏令时）
LOCAL_OFFSET_MINUTES = 8 * 60


def _local_to_utc(day: dt.date, hour: int, minute: int) -> dt.datetime:
    """本地时刻 → 库内 naive UTC。"""
    return dt.datetime.combine(day, dt.time(hour, minute)) - dt.timedelta(
        minutes=LOCAL_OFFSET_MINUTES
    )


def _word_ids(db, count: int) -> list[int]:
    return [
        row[0]
        for row in db.execute(select(Word.id).order_by(Word.id).limit(count)).all()
    ]


def _seed_day(db, user_id: int, day: dt.date, total: int, viewed: int = 0) -> None:
    """生成当日集合：total 个条目，其中前 viewed 个已浏览。"""
    ids = _word_ids(db, max(total, 1))
    daily_set = DailySet(user_id=user_id, study_date=day, created_at=utcnow())
    db.add(daily_set)
    db.flush()
    for index in range(total):
        db.add(
            DailySetItem(
                daily_set_id=daily_set.id,
                word_id=ids[index],
                order_index=index + 1,
                viewed_at=utcnow() if index < viewed else None,
            )
        )
    db.commit()


def _seed_attempt(
    db,
    user_id: int,
    kind: str,
    *,
    study_date: dt.date | None = None,
    finished: bool = True,
    total: int = 10,
    correct: int = 8,
    answers: list[tuple[bool, dt.datetime]] | None = None,
) -> int:
    """生成一轮测验 / 专项练习；answers 为 (是否正确, 作答时刻) 列表。"""
    attempt = QuizAttempt(
        user_id=user_id,
        kind=kind,
        study_date=study_date,
        started_at=utcnow(),
        finished_at=utcnow() if finished else None,
        total_count=total,
        correct_count=correct,
        wrong_count=total - correct,
    )
    db.add(attempt)
    db.flush()
    ids = _word_ids(db, max(len(answers or []), 1))
    for index, (is_correct, answered_at) in enumerate(answers or []):
        db.add(
            QuizAnswer(
                attempt_id=attempt.id,
                word_id=ids[index],
                question_type="en2zh",
                choice_index=0 if is_correct else 1,
                is_correct=is_correct,
                answered_at=answered_at,
            )
        )
    db.commit()
    return attempt.id


def _day_of(month_payload: dict, day: dt.date) -> dict:
    return next(item for item in month_payload["days"] if item["date"] == day.isoformat())


def test_learned_count_only_counts_viewed_items(client, db):
    user_id = register(client)["user"]["id"]
    day = dt.date(2026, 9, 10)
    _seed_day(db, user_id, day, total=5, viewed=3)

    body = summary_service.day_summary(db, user_id, day.isoformat())

    assert body["learned_count"] == 3


def test_daily_quiz_grouped_by_study_date(client, db):
    user_id = register(client)["user"]["id"]
    day = dt.date(2026, 9, 11)
    _seed_day(db, user_id, day, total=4, viewed=4)
    _seed_attempt(db, user_id, "daily", study_date=day, total=10, correct=7)

    body = summary_service.day_summary(db, user_id, day.isoformat())

    assert body["quiz"]["completed"] is True
    assert body["quiz"]["rounds"] == 1
    assert body["quiz"]["answered"] == 10
    assert body["quiz"]["correct"] == 7
    assert body["quiz"]["wrong"] == 3


def test_practice_grouped_by_answered_at_local_date(client, db):
    """专项练习按 answered_at 换算 Asia/Shanghai 归日（FR-013 / R-002）。"""
    user_id = register(client)["user"]["id"]
    day = dt.date(2026, 9, 12)
    _seed_day(db, user_id, day, total=3, viewed=3)
    # 本地 23:55 与次日 00:05 各答一题：必须落在两天，不合并
    _seed_attempt(
        db,
        user_id,
        "review",
        answers=[
            (True, _local_to_utc(day, 23, 55)),
            (False, _local_to_utc(day + dt.timedelta(days=1), 0, 5)),
        ],
    )

    same_day = summary_service.day_summary(db, user_id, day.isoformat())
    next_day = summary_service.day_summary(
        db, user_id, (day + dt.timedelta(days=1)).isoformat()
    )

    assert same_day["review_practice"]["answered"] == 1
    assert same_day["review_practice"]["correct"] == 1
    assert next_day["review_practice"]["answered"] == 1
    assert next_day["review_practice"]["wrong"] == 1
    # 一轮作答跨零点 → 两天各计入该轮（轮数按当日有作答计）
    assert same_day["review_practice"]["rounds"] == 1
    assert next_day["review_practice"]["rounds"] == 1


def test_levels_gray_light_deep(client, db):
    user_id = register(client)["user"]["id"]
    deep_day = dt.date(2026, 9, 1)
    light_day = dt.date(2026, 9, 2)
    gray_day = dt.date(2026, 9, 3)
    _seed_day(db, user_id, deep_day, total=6, viewed=6)
    _seed_day(db, user_id, light_day, total=6, viewed=0)

    body = summary_service.month_summary(db, user_id, "2026-09")

    assert _day_of(body, deep_day)["level"] == "deep"
    assert _day_of(body, light_day)["level"] == "light"
    assert _day_of(body, gray_day)["level"] == "gray"


def test_shade_buckets(client, db):
    user_id = register(client)["user"]["id"]
    days = {
        1: dt.date(2026, 9, 5),   # 5 词 → 1
        2: dt.date(2026, 9, 6),   # 12 词 → 2
        3: dt.date(2026, 9, 7),   # 30 词 → 3
    }
    _seed_day(db, user_id, days[1], total=5, viewed=5)
    _seed_day(db, user_id, days[2], total=12, viewed=12)
    _seed_day(db, user_id, days[3], total=30, viewed=30)

    body = summary_service.month_summary(db, user_id, "2026-09")

    assert _day_of(body, days[1])["shade"] == 1
    assert _day_of(body, days[2])["shade"] == 2
    assert _day_of(body, days[3])["shade"] == 3
    # 非深绿一律 shade = 0
    assert _day_of(body, dt.date(2026, 9, 4))["shade"] == 0


def test_only_practice_day_is_deep_with_zero_learned(client, db):
    """当天只做专项练习、未学新单词 → 仍为深绿，但学习词数为 0。"""
    user_id = register(client)["user"]["id"]
    day = dt.date(2026, 9, 8)
    _seed_attempt(
        db,
        user_id,
        "archive",
        answers=[(True, _local_to_utc(day, 20, 0)), (False, _local_to_utc(day, 20, 1))],
    )

    body = summary_service.month_summary(db, user_id, "2026-09")

    assert _day_of(body, day)["level"] == "deep"
    assert _day_of(body, day)["learned_count"] == 0


def test_month_total_matches_sum_of_days(client, db):
    user_id = register(client)["user"]["id"]
    for offset, viewed in enumerate([4, 6, 0], start=1):
        day = dt.date(2026, 9, 10 + offset)
        _seed_day(db, user_id, day, total=viewed or 5, viewed=viewed)
    _seed_attempt(
        db, user_id, "daily", study_date=dt.date(2026, 9, 11), total=10, correct=9
    )
    _seed_attempt(
        db,
        user_id,
        "review",
        answers=[(True, _local_to_utc(dt.date(2026, 9, 12), 21, 0))],
    )

    body = summary_service.month_summary(db, user_id, "2026-09")

    total = body["month_total"]
    assert total["learned_words"] == sum(item["learned_count"] for item in body["days"])
    assert total["quiz"]["answered"] == 10
    assert total["quiz"]["correct"] == 9
    assert total["quiz"]["rounds"] == 1
    assert total["review_practice"]["answered"] == 1
    assert total["active_days"] == sum(1 for item in body["days"] if item["level"] != "gray")


def test_streak_keeps_recent_segment_when_today_not_learned(client, db, monkeypatch):
    """今天还没学 → 从昨天往前数，不归零（FR-023 / US4 验收 4）。"""
    user_id = register(client)["user"]["id"]
    today = dt.date(2026, 9, 20)
    monkeypatch.setattr(summary_service, "today_date", lambda: today)
    for offset in range(1, 4):  # 17 / 18 / 19 连续三天
        _seed_day(db, user_id, today - dt.timedelta(days=offset), total=5, viewed=5)

    body = summary_service.month_summary(db, user_id, "2026-09")

    assert body["streak_days"] == 3


def test_streak_resets_after_one_day_gap(client, db, monkeypatch):
    user_id = register(client)["user"]["id"]
    today = dt.date(2026, 9, 20)
    monkeypatch.setattr(summary_service, "today_date", lambda: today)
    _seed_day(db, user_id, today - dt.timedelta(days=1), total=5, viewed=5)  # 19
    _seed_day(db, user_id, today - dt.timedelta(days=3), total=5, viewed=5)  # 17（18 中断）

    body = summary_service.month_summary(db, user_id, "2026-09")

    assert body["streak_days"] == 1


def test_streak_zero_for_month_without_activity(client, db, monkeypatch):
    """切到完全没有活动的月份 → 连续天数为 0（US4 验收 6）。"""
    user_id = register(client)["user"]["id"]
    monkeypatch.setattr(summary_service, "today_date", lambda: dt.date(2026, 9, 20))
    _seed_day(db, user_id, dt.date(2026, 9, 19), total=5, viewed=5)

    body = summary_service.month_summary(db, user_id, "2026-08")

    assert body["streak_days"] == 0
    assert body["month_total"]["learned_words"] == 0


def test_day_summary_without_record(client, db):
    user_id = register(client)["user"]["id"]
    day = dt.date(2026, 9, 25)

    body = summary_service.day_summary(db, user_id, day.isoformat())

    assert body["has_record"] is False
    assert body["learned_count"] == 0
    assert body["quiz"]["completed"] is False
    assert body["review_practice"]["answered"] == 0


def test_invalid_parameters_reject(client, db):
    user_id = register(client)["user"]["id"]

    with pytest.raises(Exception) as month_error:
        summary_service.month_summary(db, user_id, "2026/09")
    with pytest.raises(Exception) as date_error:
        summary_service.day_summary(db, user_id, "2026-09-32")

    assert getattr(month_error.value, "code", "") == "invalid_month"
    assert getattr(date_error.value, "code", "") == "invalid_date"
