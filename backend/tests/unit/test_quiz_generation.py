"""出题规则单元测试：题型随机、4 选项、1 正确、干扰项去重、确定性可复现。"""

from __future__ import annotations

import pytest

from app.services import quiz_service

pytestmark = pytest.mark.unit


def test_question_shape_and_uniqueness(db):
    word_ids = [1, 2, 3, 4, 5]
    questions = quiz_service.build_questions(db, word_ids, seed=101)

    assert len(questions) == len(word_ids)
    for question in questions:
        assert len(question.options) == 4
        assert len(set(question.options)) == 4  # 选项文本去重
        assert question.question_type in ("en2zh", "zh2en")
        assert 0 <= question.correct_index < 4
        assert question.options[question.correct_index]


def test_distractors_never_equal_correct_text(db):
    word_ids = list(range(1, 21))
    for question in quiz_service.build_questions(db, word_ids, seed=7):
        correct = question.options[question.correct_index]
        assert sum(1 for option in question.options if option == correct) == 1


def test_generation_is_deterministic_per_attempt_seed(db):
    word_ids = [3, 6, 9]
    first = quiz_service.build_questions(db, word_ids, seed=55)
    second = quiz_service.build_questions(db, word_ids, seed=55)
    third = quiz_service.build_questions(db, word_ids, seed=56)

    assert [(q.question_type, tuple(q.options)) for q in first] == [
        (q.question_type, tuple(q.options)) for q in second
    ]
    # 不同 attempt（seed）应产生不同题目，验证"随机"确实存在
    assert [(q.question_type, tuple(q.options)) for q in first] != [
        (q.question_type, tuple(q.options)) for q in third
    ]


def test_daily_question_order_is_shuffled_but_stable_per_attempt(db):
    """FR-024 补充：题序不等于学习顺序，但同一轮内固定。"""
    word_ids = list(range(1, 21))

    first = [q.word_id for q in quiz_service.shuffle_questions(
        quiz_service.build_questions(db, word_ids, seed=101), seed=101
    )]
    again = [q.word_id for q in quiz_service.shuffle_questions(
        quiz_service.build_questions(db, word_ids, seed=101), seed=101
    )]
    other = [q.word_id for q in quiz_service.shuffle_questions(
        quiz_service.build_questions(db, word_ids, seed=101), seed=102
    )]

    assert set(first) == set(word_ids)  # 覆盖当日全部单词，不漏题
    assert first == again  # 同一轮顺序固定
    assert first != other  # 不同轮换序
    assert first != word_ids  # 与学习顺序不一致


def test_both_question_types_can_appear(db):
    word_ids = list(range(1, 61))
    types = {
        question.question_type
        for question in quiz_service.build_questions(db, word_ids, seed=2024)
    }
    assert types == {"en2zh", "zh2en"}
