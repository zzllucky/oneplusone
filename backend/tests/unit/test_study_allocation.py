"""当日日期边界与每日分配规则单元测试。"""

from __future__ import annotations

import datetime as dt

import pytest

from app.models.word import Word
from app.services import auth_service, study_service

pytestmark = pytest.mark.unit


def _make_user(db, login_name: str) -> int:
    return auth_service.register(
        db, login_name=login_name, nickname="测试用户", password="abc123"
    ).id


def test_today_date_uses_shanghai_timezone():
    # UTC 2026-09-28T16:30 → 上海 2026-09-29 00:30
    moment = dt.datetime(2026, 9, 28, 16, 30, tzinfo=dt.timezone.utc)
    assert study_service.today_date(moment).isoformat() == "2026-09-29"

    # UTC 2026-09-28T15:59 → 上海 2026-09-28 23:59
    moment = dt.datetime(2026, 9, 28, 15, 59, tzinfo=dt.timezone.utc)
    assert study_service.today_date(moment).isoformat() == "2026-09-28"


def test_allocation_takes_min_of_goal_and_unlearned(db):
    goal = 5
    user_id = _make_user(db, "user1")
    daily_set = study_service.get_or_create_today_set(db, user_id=user_id, daily_goal=goal)

    assert len(daily_set.items) == goal
    assert [item.order_index for item in sorted(daily_set.items, key=lambda i: i.order_index)] == [
        1,
        2,
        3,
        4,
        5,
    ]

    word_ids = [item.word_id for item in daily_set.items]
    assert word_ids == sorted(word_ids)  # 按 words.id 升序


def test_second_call_returns_same_set(db):
    user_id = _make_user(db, "user1")
    first = study_service.get_or_create_today_set(db, user_id=user_id, daily_goal=5)
    second = study_service.get_or_create_today_set(db, user_id=user_id, daily_goal=5)

    assert first.id == second.id
    assert len(second.items) == len(first.items)


def test_already_assigned_words_are_not_reused(db):
    user_one = _make_user(db, "user1")
    user_two = _make_user(db, "user2")
    first = study_service.get_or_create_today_set(db, user_id=user_one, daily_goal=3)
    used = {item.word_id for item in first.items}

    second = study_service.get_or_create_today_set(db, user_id=user_two, daily_goal=3)
    # 另一个用户从未学过，仍然从头分配
    assert {item.word_id for item in second.items} == {1, 2, 3}

    # 同一用户：模拟跨日（直接改日期）后应跳过已学单词
    first.study_date = first.study_date - dt.timedelta(days=1)
    db.commit()
    third = study_service.get_or_create_today_set(db, user_id=user_one, daily_goal=3)
    assert not ({item.word_id for item in third.items} & used)


def test_library_exhausted_when_remaining_less_than_goal(db):
    user_id = _make_user(db, "user1")
    total = db.query(Word).count()
    study_service.get_or_create_today_set(db, user_id=user_id, daily_goal=total)
    summary = study_service.today_summary(db, user_id=user_id, daily_goal=total + 10)

    assert summary.library_exhausted is True
    assert summary.total_count == total


def test_mark_viewed_is_idempotent(db):
    user_id = _make_user(db, "user1")
    daily_set = study_service.get_or_create_today_set(db, user_id=user_id, daily_goal=3)
    word_id = sorted(daily_set.items, key=lambda i: i.order_index)[0].word_id

    first_view = study_service.mark_viewed(db, user_id=user_id, word_id=word_id)
    assert first_view[0] is True

    item = [i for i in daily_set.items if i.word_id == word_id][0]
    first_time = item.viewed_at

    second_view = study_service.mark_viewed(db, user_id=user_id, word_id=word_id)
    assert second_view[0] is False  # 重复提交不再视为新浏览
    assert item.viewed_at == first_time  # 保留首次时间
