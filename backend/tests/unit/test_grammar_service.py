"""语法服务单元测试（US1 大纲 / US2 学卡）：真实 SQLite + ORM 造数，禁用 mock。

覆盖：
- 大纲按 module + order_index 分组与排序
- mastered_count / wrong_count 聚合
- 无进度时 status='not_started'
- question_count 只统计 source='bank'
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import func, select

from app.errors import AppError
from app.models import GrammarQuestion
from app.models.base import utcnow
from app.models.grammar import GrammarOption, GrammarPoint
from app.models.grammar_progress import GrammarPointProgress, GrammarWrongPoint
from app.services import grammar_service
from tests.conftest import register

pytestmark = pytest.mark.unit

NO_USER = 999999  # 不存在的用户：进度与错题均为空


def _register(client, login_name: str = "gstu1") -> int:
    return int(register(client, login_name=login_name)["user"]["id"])


def _first_point_id(db) -> str:
    return db.scalar(select(GrammarPoint.id))


def test_outline_covers_all_points_grouped_by_module(db) -> None:
    data = grammar_service.list_outline(db, NO_USER)

    assert data["total_points"] == 82
    modules = data["modules"]
    assert sum(len(module["points"]) for module in modules) == 82
    # 模块按模块码升序
    assert [module["module"] for module in modules] == sorted(
        module["module"] for module in modules
    )
    # 同一字母下的不同模块不得被合并（T 下 8 个时态、F 下不定式与动名词）
    keys = [(module["module"], module["module_name"]) for module in modules]
    assert len(keys) == len(set(keys))
    assert len(modules) == 20


def test_outline_points_sorted_by_order_index(db) -> None:
    data = grammar_service.list_outline(db, NO_USER)

    for module in data["modules"]:
        expected = [
            row[0]
            for row in db.execute(
                select(GrammarPoint.id)
                .where(
                    GrammarPoint.module == module["module"],
                    GrammarPoint.module_name == module["module_name"],
                )
                .order_by(GrammarPoint.order_index, GrammarPoint.id)
            ).all()
        ]
        assert [point["id"] for point in module["points"]] == expected


def test_outline_defaults_to_not_started(db) -> None:
    data = grammar_service.list_outline(db, NO_USER)

    assert data["mastered_count"] == 0
    assert data["wrong_count"] == 0
    for module in data["modules"]:
        for point in module["points"]:
            assert point["status"] == "not_started"
            assert point["has_wrong"] is False


def test_outline_question_count_only_bank(db) -> None:
    data = grammar_service.list_outline(db, NO_USER)

    counts = {
        point["id"]: point["question_count"]
        for module in data["modules"]
        for point in module["points"]
    }
    bank_counts = dict(
        db.execute(
            select(GrammarQuestion.point_id, func.count())
            .where(GrammarQuestion.source == "bank")
            .group_by(GrammarQuestion.point_id)
        ).all()
    )
    for point_id, count in counts.items():
        assert count == bank_counts.get(point_id, 0)


def test_outline_aggregates_mastered_and_wrong(client, db) -> None:
    user_id = _register(client)
    point_id = _first_point_id(db)

    db.add(
        GrammarPointProgress(
            user_id=user_id,
            point_id=point_id,
            status="mastered",
            check_total=3,
            check_correct=3,
            studied_at=utcnow(),
            mastered_at=utcnow(),
            updated_at=utcnow(),
        )
    )
    db.add(
        GrammarWrongPoint(
            user_id=user_id,
            point_id=point_id,
            wrong_count=2,
            correct_streak=0,
            added_at=utcnow(),
            last_wrong_at=utcnow(),
        )
    )
    db.commit()

    data = grammar_service.list_outline(db, user_id)

    assert data["mastered_count"] == 1
    assert data["wrong_count"] == 1
    point = next(
        item
        for module in data["modules"]
        for item in module["points"]
        if item["id"] == point_id
    )
    assert point["status"] == "mastered"
    assert point["has_wrong"] is True


def test_outline_isolated_between_users(client, db) -> None:
    """FR-019：同一份数据在不同账号之间互不可见。"""
    user_a = _register(client, "gstuA")
    user_b = _register(client, "gstuB")
    point_id = _first_point_id(db)

    db.add(
        GrammarPointProgress(
            user_id=user_a,
            point_id=point_id,
            status="mastered",
            updated_at=utcnow(),
        )
    )
    db.commit()

    assert grammar_service.list_outline(db, user_a)["mastered_count"] == 1
    assert grammar_service.list_outline(db, user_b)["mastered_count"] == 0


# ---------------------------------------------------------------- US2 学卡


def _correct_key(db, question_id: str) -> str:
    return db.scalar(
        select(GrammarOption.key).where(
            GrammarOption.question_id == question_id, GrammarOption.is_correct.is_(True)
        )
    )


def _wrong_key(db, question_id: str) -> str:
    return db.scalar(
        select(GrammarOption.key).where(
            GrammarOption.question_id == question_id, GrammarOption.is_correct.is_(False)
        )
    )


def test_mark_viewed_sets_learning_and_is_idempotent(client, db) -> None:
    user_id = _register(client, "gview")
    point_id = "G-A01"

    first = grammar_service.mark_viewed(db, user_id, point_id)
    assert first["status"] == "learning"
    assert first["studied_at"] is not None

    studied_at = first["studied_at"]
    second = grammar_service.mark_viewed(db, user_id, point_id)
    assert second["status"] == "learning"
    assert second["studied_at"] == studied_at


def test_mark_viewed_does_not_downgrade_mastered(client, db) -> None:
    user_id = _register(client, "gmaster")
    point_id = "G-A01"
    db.add(
        GrammarPointProgress(
            user_id=user_id,
            point_id=point_id,
            status="mastered",
            mastered_at=utcnow(),
            updated_at=utcnow(),
        )
    )
    db.commit()

    assert grammar_service.mark_viewed(db, user_id, point_id)["status"] == "mastered"


def test_card_attempt_all_correct_marks_mastered(client, db) -> None:
    user_id = _register(client, "gcard1")
    point_id = "G-A01"
    attempt, questions = grammar_service.start_attempt(db, user_id, point_id, "card")
    assert questions, "卡内检测题不应为空"
    assert attempt.source == "card"

    for question in questions:
        grammar_service.record_answer(
            db, user_id, attempt.id, question.id, _correct_key(db, question.id)
        )

    result = grammar_service.finish_attempt(db, user_id, attempt.id)
    assert result["mastered"] is True
    assert result["status"] == "mastered"

    progress = db.scalar(
        select(GrammarPointProgress).where(
            GrammarPointProgress.user_id == user_id,
            GrammarPointProgress.point_id == point_id,
        )
    )
    assert progress.status == "mastered"
    assert progress.mastered_at is not None


def test_card_attempt_with_wrong_answer_keeps_learning(client, db) -> None:
    user_id = _register(client, "gcard2")
    point_id = "G-A01"
    attempt, questions = grammar_service.start_attempt(db, user_id, point_id, "card")

    wrong_key = _wrong_key(db, questions[0].id)
    grammar_service.record_answer(db, user_id, attempt.id, questions[0].id, wrong_key)
    for question in questions[1:]:
        grammar_service.record_answer(
            db, user_id, attempt.id, question.id, _correct_key(db, question.id)
        )

    result = grammar_service.finish_attempt(db, user_id, attempt.id)
    assert result["mastered"] is False
    assert result["status"] == "learning"


def test_guess_feedback_returns_selected_option_feedback(db) -> None:
    feedback = grammar_service.get_guess_feedback(db, "G-A01", "A")
    assert feedback, "应返回所选选项的反馈"

    with pytest.raises(AppError) as excinfo:
        grammar_service.get_guess_feedback(db, "G-A01", "Z")
    assert excinfo.value.code == "invalid_choice_key"


# ---------------------------------------------------------------- US3 练习


def _bank_point_id(db) -> str:
    return db.scalar(
        select(GrammarQuestion.point_id)
        .where(GrammarQuestion.source == "bank")
        .group_by(GrammarQuestion.point_id)
        .order_by(GrammarQuestion.point_id)
        .limit(1)
    )


def _point_without_bank(db) -> str:
    bank_ids = [
        row[0]
        for row in db.execute(
            select(GrammarQuestion.point_id).where(GrammarQuestion.source == "bank")
        ).all()
    ]
    return db.scalar(
        select(GrammarPoint.id)
        .where(GrammarPoint.id.notin_(bank_ids))
        .order_by(GrammarPoint.id)
        .limit(1)
    )


def test_bank_attempt_orders_by_level_then_index(client, db) -> None:
    user_id = _register(client, "gbank1")
    point_id = _bank_point_id(db)
    attempt, questions = grammar_service.start_attempt(db, user_id, point_id, "bank")

    assert attempt.source == "bank"
    levels = [question.level for question in questions]
    assert levels == sorted(levels), "层级必须按 L1 → L2 → L3 递进（不洗牌）"
    for level in dict.fromkeys(levels):
        indexes = [q.order_index for q in questions if q.level == level]
        assert indexes == sorted(indexes)


def test_bank_attempt_filters_by_level(client, db) -> None:
    user_id = _register(client, "gbank2")
    point_id = _bank_point_id(db)
    _attempt, questions = grammar_service.start_attempt(
        db, user_id, point_id, "bank", level="L2"
    )

    assert questions
    assert {question.level for question in questions} == {"L2"}


def test_bank_attempt_without_questions_raises(client, db) -> None:
    user_id = _register(client, "gbank3")
    point_id = _point_without_bank(db)

    with pytest.raises(AppError) as excinfo:
        grammar_service.start_attempt(db, user_id, point_id, "bank")
    assert excinfo.value.code == "no_grammar_questions"


def test_bank_finish_does_not_change_status(client, db) -> None:
    user_id = _register(client, "gbank4")
    point_id = _bank_point_id(db)
    attempt, questions = grammar_service.start_attempt(db, user_id, point_id, "bank")

    for question in questions:
        grammar_service.record_answer(
            db, user_id, attempt.id, question.id, _correct_key(db, question.id)
        )
    result = grammar_service.finish_attempt(db, user_id, attempt.id)

    assert result["mastered"] is False
    assert result["status"] == "not_started"


def test_restart_creates_new_attempt(client, db) -> None:
    """中途退出后再次发起：新建轮次，旧轮次保持未完成（US3-AC4）。"""
    user_id = _register(client, "gbank5")
    point_id = _bank_point_id(db)
    first, questions = grammar_service.start_attempt(db, user_id, point_id, "bank")
    grammar_service.record_answer(
        db, user_id, first.id, questions[0].id, _correct_key(db, questions[0].id)
    )
    second, _again = grammar_service.start_attempt(db, user_id, point_id, "bank")

    assert second.id != first.id
    assert first.finished_at is None


# ------------------------------------------------------------ US4 错题回链


def _wrong_row(db, user_id: int, point_id: str) -> GrammarWrongPoint | None:
    return db.scalar(
        select(GrammarWrongPoint).where(
            GrammarWrongPoint.user_id == user_id,
            GrammarWrongPoint.point_id == point_id,
        )
    )


def _answer_once(db, user_id: int, point_id: str, correct: bool) -> dict:
    """开一轮练习并对首题作答（correct 决定对错），返回判分结果。"""
    attempt, questions = grammar_service.start_attempt(db, user_id, point_id, "bank")
    key = (
        _correct_key(db, questions[0].id)
        if correct
        else _wrong_key(db, questions[0].id)
    )
    return grammar_service.record_answer(db, user_id, attempt.id, questions[0].id, key)


def test_wrong_point_insert_then_accumulate(client, db) -> None:
    user_id = _register(client, "gwrong1")
    point_id = _bank_point_id(db)

    first = _answer_once(db, user_id, point_id, correct=False)
    assert first["added_to_wrong_points"] is True
    row = _wrong_row(db, user_id, point_id)
    assert row.wrong_count == 1
    assert row.correct_streak == 0
    added_at = row.added_at

    second = _answer_once(db, user_id, point_id, correct=False)
    assert second["added_to_wrong_points"] is False
    row = _wrong_row(db, user_id, point_id)
    assert row.wrong_count == 2
    assert row.correct_streak == 0
    assert row.added_at == added_at, "重复答错不得更新加入时间"
    assert row.last_wrong_at >= added_at


def test_wrong_point_removed_after_streak(client, db) -> None:
    user_id = _register(client, "gwrong2")
    point_id = _bank_point_id(db)

    _answer_once(db, user_id, point_id, correct=False)
    assert _wrong_row(db, user_id, point_id) is not None

    # 连续答对 1 次：保留，streak=1
    streak_one = _answer_once(db, user_id, point_id, correct=True)
    assert streak_one["removed_from_wrong_points"] is False
    assert streak_one["correct_streak"] == 1

    # 连续答对第 2 次：达到阈值，移出
    streak_two = _answer_once(db, user_id, point_id, correct=True)
    assert streak_two["removed_from_wrong_points"] is True
    assert _wrong_row(db, user_id, point_id) is None


def test_wrong_point_streak_resets_on_wrong(client, db) -> None:
    user_id = _register(client, "gwrong3")
    point_id = _bank_point_id(db)

    _answer_once(db, user_id, point_id, correct=False)
    _answer_once(db, user_id, point_id, correct=True)
    assert _wrong_row(db, user_id, point_id).correct_streak == 1

    _answer_once(db, user_id, point_id, correct=False)
    assert _wrong_row(db, user_id, point_id).correct_streak == 0


def test_list_wrong_points_sorted_by_added_at(client, db) -> None:
    user_id = _register(client, "gwrong4")
    points = list(
        db.scalars(select(GrammarPoint.id).order_by(GrammarPoint.id).limit(2)).all()
    )
    now = utcnow()
    db.add(
        GrammarWrongPoint(
            user_id=user_id,
            point_id=points[1],
            added_at=now,
            last_wrong_at=now,
        )
    )
    db.add(
        GrammarWrongPoint(
            user_id=user_id,
            point_id=points[0],
            added_at=now - dt.timedelta(hours=1),
            last_wrong_at=now - dt.timedelta(hours=1),
        )
    )
    db.commit()

    data = grammar_service.list_wrong_points(db, user_id)
    assert data["total"] == 2
    assert [item["point_id"] for item in data["items"]] == [points[0], points[1]]
    assert data["items"][0]["title"]


def test_sanitize_payload_removes_answers() -> None:
    payload = {
        "guess": {
            "question": "为什么？",
            "options": [
                {"key": "A", "text": "因为多音节", "feedback": "对！"},
                {"key": "B", "text": "因为结尾", "feedback": "不对——"},
            ],
            "answer": "A",
        },
        "rule": {"rule": "规则", "answer": "A"},
    }

    cleaned = grammar_service.sanitize_payload(payload)

    assert "answer" not in cleaned["guess"]
    assert "answer" not in cleaned["rule"]
    for option in cleaned["guess"]["options"]:
        assert set(option) == {"key", "text"}
    assert "feedback" not in cleaned["guess"]["options"][0]
