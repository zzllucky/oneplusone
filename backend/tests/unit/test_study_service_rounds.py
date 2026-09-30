"""学习服务在轮次机制下的取词行为（T008）：跨轮开启、单日不混轮、exhausted 新语义。"""

from __future__ import annotations

import datetime as dt

import pytest

from app.models.word import Word
from app.services import auth_service, round_service, study_service

pytestmark = pytest.mark.unit


def _make_user(db, login_name: str = "user1") -> int:
    return auth_service.register(
        db, login_name=login_name, nickname="测试用户", password="abc123"
    ).id


def _total(db) -> int:
    return db.query(Word).count()


def _shift_today(monkeypatch, days: int) -> None:
    base = study_service.today_date()

    monkeypatch.setattr(
        study_service, "today_date", lambda now=None: base + dt.timedelta(days=days)
    )


def _push_cursor_to_remaining(db, user_id: int, remaining: int) -> None:
    """把当前轮游标推进到"只剩 remaining 个单词"。"""
    total = _total(db)
    ids = round_service.allocate_word_ids(db, user_id, total - remaining)
    round_service.advance_cursor(db, user_id, ids)


def test_next_day_starts_new_round_from_library_head(db, monkeypatch):
    """本轮耗尽后，次日分配自动开启新一轮并从词库首个单词开始（FR-001 / FR-012）。"""
    user_id = _make_user(db)
    first = study_service.get_or_create_today_set(db, user_id, _total(db))
    assert len(first.items) == _total(db)

    _shift_today(monkeypatch, 1)
    second = study_service.get_or_create_today_set(db, user_id, 5)

    head_ids = [row[0] for row in db.query(Word.id).order_by(Word.id).limit(5)]
    assert [item.word_id for item in second.items] == head_ids


def test_day_set_never_mixes_rounds(db):
    """当前轮剩余不足每日目标时，当日只分配剩余部分，不从新一轮借词（FR-009）。"""
    user_id = _make_user(db)
    _push_cursor_to_remaining(db, user_id, remaining=3)

    daily_set = study_service.get_or_create_today_set(db, user_id, 10)

    assert len(daily_set.items) == 3


def test_library_exhausted_means_remaining_less_than_goal(db):
    """library_exhausted = 本轮剩余不足每日目标（不再是"词库被学完"）。"""
    user_id = _make_user(db)
    _push_cursor_to_remaining(db, user_id, remaining=3)

    study_service.get_or_create_today_set(db, user_id, 10)
    summary = study_service.today_summary(db, user_id, daily_goal=10)

    assert summary.total_count == 3
    assert summary.library_exhausted is True


def test_library_not_exhausted_when_goal_matches(db):
    user_id = _make_user(db)
    study_service.get_or_create_today_set(db, user_id, 5)
    summary = study_service.today_summary(db, user_id, daily_goal=5)

    assert summary.library_exhausted is False


def test_viewed_progress_unlocks_quiz_in_new_round(db, monkeypatch):
    """新一轮内"全部浏览 → 解锁测验"规则不变（US3 回归）。"""
    user_id = _make_user(db)
    study_service.get_or_create_today_set(db, user_id, _total(db))

    _shift_today(monkeypatch, 1)
    daily_set = study_service.get_or_create_today_set(db, user_id, 3)
    for item in sorted(daily_set.items, key=lambda i: i.order_index):
        study_service.mark_viewed(db, user_id, item.word_id)

    summary = study_service.today_summary(db, user_id, daily_goal=3)
    assert summary.all_viewed is True
    assert summary.quiz_unlocked is True
