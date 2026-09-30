"""轮次服务单元测试：游标推进 / 跨轮 / 覆盖与完成 / 补记 / 进度（T006）。"""

from __future__ import annotations

import datetime as dt

import pytest

from app.models.study_round import StudyRound
from app.models.word import Word
from app.services import auth_service, round_service, study_service

pytestmark = pytest.mark.unit


def _make_user(db, login_name: str = "user1") -> int:
    return auth_service.register(
        db, login_name=login_name, nickname="测试用户", password="abc123"
    ).id


def _total(db) -> int:
    return db.query(Word).count()


def _open_round(db, user_id: int) -> StudyRound | None:
    return db.query(StudyRound).filter(
        StudyRound.user_id == user_id, StudyRound.completed_at.is_(None)
    ).first()


def _shift_today(monkeypatch, days: int) -> None:
    base = study_service.today_date()

    def fake_today(now=None):
        return base + dt.timedelta(days=days)

    monkeypatch.setattr(study_service, "today_date", fake_today)


def test_first_round_created_lazily(db):
    user_id = _make_user(db)
    round_ = round_service.ensure_open_round(db, user_id)

    assert round_.round_no == 1
    assert round_.cursor_word_id == db.query(Word.id).order_by(Word.id).first()[0]
    assert round_.covered_at is None and round_.completed_at is None


def test_cursor_advances_after_allocation(db):
    user_id = _make_user(db)
    ids = round_service.allocate_word_ids(db, user_id, 5)
    round_service.advance_cursor(db, user_id, ids)

    round_ = _open_round(db, user_id)
    assert ids == sorted(ids)
    assert round_.cursor_word_id == ids[-1] + 1


def test_cursor_beyond_library_marks_covered(db):
    user_id = _make_user(db)
    ids = round_service.allocate_word_ids(db, user_id, _total(db))
    round_service.advance_cursor(db, user_id, ids)

    round_ = _open_round(db, user_id)
    assert len(ids) == _total(db)
    assert round_.covered_at is not None
    assert round_.completed_at is None  # 未做测验不算完成（FR-004）


def test_quiz_signal_completes_covered_round(db):
    user_id = _make_user(db)
    ids = round_service.allocate_word_ids(db, user_id, _total(db))
    round_service.advance_cursor(db, user_id, ids)

    assert round_service.mark_completed(db, user_id) is True
    assert round_service.completed_rounds(db, user_id) == 1

    # 重复信号不重复计数
    assert round_service.mark_completed(db, user_id) is False
    assert round_service.completed_rounds(db, user_id) == 1


def test_quiz_signal_before_covered_does_not_complete(db):
    user_id = _make_user(db)
    round_service.allocate_word_ids(db, user_id, 3)

    assert round_service.mark_completed(db, user_id) is False
    assert round_service.completed_rounds(db, user_id) == 0


def test_settle_records_round_when_covered_day_passed(db, monkeypatch):
    """轮末只浏览未测验：次日补记为已完成（FR-014），且不伪造测验成绩。"""
    user_id = _make_user(db)
    ids = round_service.allocate_word_ids(db, user_id, _total(db))
    round_service.advance_cursor(db, user_id, ids)

    round_ = _open_round(db, user_id)
    round_.covered_at = dt.datetime.now(dt.timezone.utc).replace(
        tzinfo=None
    ) - dt.timedelta(days=1)
    db.commit()

    _shift_today(monkeypatch, 0)
    count = round_service.settle_pending_rounds(db, user_id)

    assert count == 1
    assert round_service.completed_rounds(db, user_id) == 1


def test_settle_runs_from_read_entry(db, monkeypatch):
    """补记必须在读取入口触发：只看 progress（不分配）也要补记（SC-006）。"""
    user_id = _make_user(db)
    ids = round_service.allocate_word_ids(db, user_id, _total(db))
    round_service.advance_cursor(db, user_id, ids)

    round_ = _open_round(db, user_id)
    round_.covered_at = dt.datetime.now(dt.timezone.utc).replace(
        tzinfo=None
    ) - dt.timedelta(days=1)
    db.commit()

    progress = round_service.progress(db, user_id)

    assert round_service.completed_rounds(db, user_id) == 1
    # 补记后应已开启新一轮
    assert progress.round_no == 2


def test_settle_does_not_fire_on_same_day(db):
    """覆盖日仍是今天时，不补记 —— 学生当天还有机会完成测验。"""
    user_id = _make_user(db)
    ids = round_service.allocate_word_ids(db, user_id, _total(db))
    round_service.advance_cursor(db, user_id, ids)

    progress = round_service.progress(db, user_id)

    assert round_service.completed_rounds(db, user_id) == 0
    assert progress.pending_quiz is True


def test_progress_uses_cursor(db):
    user_id = _make_user(db)
    ids = round_service.allocate_word_ids(db, user_id, 7)
    round_service.advance_cursor(db, user_id, ids)

    progress = round_service.progress(db, user_id)

    assert progress.round_no == 1
    assert progress.learned_count == 7
    assert progress.total_count == _total(db)
    assert progress.pending_quiz is False


def test_long_break_continues_current_round(db, monkeypatch):
    """中断数月回来：继续当前轮剩余部分，不重置进度（US1 验收 5）。"""
    user_id = _make_user(db)
    ids = round_service.allocate_word_ids(db, user_id, 10)
    round_service.advance_cursor(db, user_id, ids)

    _shift_today(monkeypatch, 120)
    progress = round_service.progress(db, user_id)
    next_ids = round_service.allocate_word_ids(db, user_id, 5)

    assert progress.round_no == 1
    assert progress.learned_count == 10
    assert next_ids[0] == ids[-1] + 1


def test_only_one_open_round_under_parallel_sessions(db):
    """并发 / 多设备：单账号至多一个进行中轮次（部分唯一索引 + 单写入口，T028）。"""
    from sqlalchemy.exc import IntegrityError

    from app import db as db_module

    user_id = _make_user(db)
    first = round_service.ensure_open_round(db, user_id)

    other = db_module.SessionLocal()
    try:
        second = round_service.ensure_open_round(other, user_id)
        assert second.round_no == first.round_no
    except IntegrityError:
        other.rollback()  # 唯一索引拒绝第二行：并发安全
    finally:
        other.close()

    open_count = (
        db.query(StudyRound)
        .filter(StudyRound.user_id == user_id, StudyRound.completed_at.is_(None))
        .count()
    )
    assert open_count == 1


def test_duplicate_open_round_rejected_by_index(db):
    """绕过服务层直接插入第二个"进行中"轮次 → 数据库约束拒绝（T028）。"""
    from sqlalchemy.exc import IntegrityError

    from app.services import study_service

    user_id = _make_user(db)
    round_service.ensure_open_round(db, user_id)

    with pytest.raises(IntegrityError):
        db.add(
            StudyRound(
                user_id=user_id,
                round_no=99,
                cursor_word_id=1,
                started_on=study_service.today_date(),
            )
        )
        db.commit()
    db.rollback()


def test_only_one_open_round_per_account(db):
    user_id = _make_user(db)
    first = round_service.ensure_open_round(db, user_id)
    second = round_service.ensure_open_round(db, user_id)

    assert first.id == second.id
    open_count = (
        db.query(StudyRound)
        .filter(StudyRound.user_id == user_id, StudyRound.completed_at.is_(None))
        .count()
    )
    assert open_count == 1
