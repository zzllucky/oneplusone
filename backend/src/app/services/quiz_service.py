"""测验与专项练习服务。

四条硬性规则在本模块固化为代码结构（R-008）：
- ``start_daily_quiz`` 校验"全部浏览" → 否则 409 `quiz_locked`
- ``record_daily_quiz_answer`` 答对 → **不执行任何删除**（FR-026）
- ``record_review_answer`` 答对 → 连续答对 ``REVIEW_REMOVE_STREAK`` 次后删除错题
  （**全项目唯一**删除路径，FR-038）
- 错题库（``wrong_word_archive``）**永不删除**：答对只不动，答错仅累加次数
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError
from app.models.base import utcnow
from app.models.daily_set import DailySet, DailySetItem
from app.models.quiz import QuizAnswer, QuizAttempt
from app.models.word import Word
from app.models.wrong_word import WrongWord
from app.models.wrong_word_archive import WrongWordArchive
from app.services import round_service, study_service, wrong_word_service

QUESTION_TYPES = ("en2zh", "zh2en")

# 错题本移出所需连续答对次数：答对 1 次只记 streak，达到该值才移除；答错归零
REVIEW_REMOVE_STREAK = 2
# 错题库专项练习单轮最大题量：优先出错误次数多的顽固词
ARCHIVE_QUIZ_LIMIT = 50


@dataclass
class GeneratedQuestion:
    word_id: int
    question_type: str
    prompt: str
    options: list[str]
    correct_index: int


def _rng(seed: int, word_id: int) -> random.Random:
    """按 (attempt_id, word_id) 播种：出题与批改两次生成结果完全一致。"""
    return random.Random(f"{seed}:{word_id}")


def _build_question(word: Word, pool: list[Word], seed: int) -> GeneratedQuestion:
    rng = _rng(seed, word.id)
    question_type = rng.choice(QUESTION_TYPES)

    if question_type == "en2zh":
        correct_text = word.meaning_zh
        prompt = word.spelling
        field = "meaning_zh"
    else:
        correct_text = word.spelling
        prompt = word.meaning_zh
        field = "spelling"

    seen = {correct_text}
    distractors: list[str] = []
    candidates = [item for item in pool if item.id != word.id]
    rng.shuffle(candidates)
    for candidate in candidates:
        text = getattr(candidate, field)
        if text in seen:
            continue
        seen.add(text)
        distractors.append(text)
        if len(distractors) == 3:
            break

    while len(distractors) < 3:  # 词库极小时的兜底，保证恒为 4 个选项
        filler = f"{field}-{len(distractors) + 1}"
        if filler not in seen:
            seen.add(filler)
            distractors.append(filler)

    options = distractors + [correct_text]
    rng.shuffle(options)
    return GeneratedQuestion(
        word_id=word.id,
        question_type=question_type,
        prompt=prompt,
        options=options,
        correct_index=options.index(correct_text),
    )


def shuffle_questions(
    questions: list[GeneratedQuestion], seed: int
) -> list[GeneratedQuestion]:
    """按本轮测验（attempt）洗牌题序：题序与学习顺序解耦，但同一轮内固定。"""
    ordered = list(questions)
    random.Random(f"order:{seed}").shuffle(ordered)
    return ordered


def _library_pool(db: Session) -> list[Word]:
    return list(db.scalars(select(Word).order_by(Word.id)).all())


def build_questions(db: Session, word_ids: list[int], seed: int) -> list[GeneratedQuestion]:
    """按 (seed, word_id) 确定性出题：题型随机、4 选项、1 正确、干扰项文本去重。"""
    pool = _library_pool(db)
    words = {word.id: word for word in pool}
    return [
        _build_question(words[word_id], pool, seed)
        for word_id in word_ids
        if word_id in words
    ]


def _unfinished_attempt(db: Session, user_id: int, kind: str) -> QuizAttempt | None:
    return db.scalar(
        select(QuizAttempt).where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.kind == kind,
            QuizAttempt.finished_at.is_(None),
        )
    )


def _daily_word_ids(db: Session, user_id: int, study_date) -> list[int]:
    daily_set = db.scalar(
        select(DailySet).where(
            DailySet.user_id == user_id, DailySet.study_date == study_date
        )
    )
    if daily_set is None:
        return []
    items = sorted(daily_set.items, key=lambda item: item.order_index)
    return [item.word_id for item in items]


def start_daily_quiz(db: Session, user_id: int) -> tuple[QuizAttempt, list[GeneratedQuestion]]:
    """开启今日测验：未完成全部浏览 → 409 `quiz_locked`。

    003 注：本规则在**每一轮**中都与首轮一致 —— 新一轮同样"先浏览后解锁"，
    词库耗尽后也不再永久锁死（US3 回归见
    ``tests/integration/test_round_existing_rules.py``）。
    """
    from app.services.settings_service import get_daily_goal

    goal = get_daily_goal(db, user_id)
    summary = study_service.today_summary(db, user_id, goal)
    study_date = summary.study_date

    if not summary.quiz_unlocked:
        raise AppError("quiz_locked", status_code=409)

    attempt = db.scalar(
        select(QuizAttempt).where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.kind == "daily",
            QuizAttempt.study_date == study_date,
            QuizAttempt.finished_at.is_(None),
        )
    )
    if attempt is None:
        word_ids = _daily_word_ids(db, user_id, study_date)
        attempt = QuizAttempt(
            user_id=user_id,
            kind="daily",
            study_date=study_date,
            started_at=utcnow(),
            total_count=len(word_ids),
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

    word_ids = _daily_word_ids(db, user_id, attempt.study_date)
    # 题目覆盖当日全部单词，题序按本轮随机（进入测验后顺序固定）
    return attempt, shuffle_questions(build_questions(db, word_ids, attempt.id), attempt.id)


def start_review_quiz(db: Session, user_id: int) -> tuple[QuizAttempt, list[GeneratedQuestion]]:
    """开启错题专项练习：题目仅来自当前错题本；空 → 409 `no_wrong_words`。"""
    word_ids = wrong_word_service.wrong_word_ids(db, user_id)
    if not word_ids:
        raise AppError("no_wrong_words", status_code=409)

    attempt = _unfinished_attempt(db, user_id, "review")
    if attempt is None:
        attempt = QuizAttempt(
            user_id=user_id,
            kind="review",
            study_date=None,
            started_at=utcnow(),
            total_count=len(word_ids),
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

    current_ids = wrong_word_service.wrong_word_ids(db, user_id)
    answered_ids = list(
        db.scalars(
            select(QuizAnswer.word_id).where(QuizAnswer.attempt_id == attempt.id)
        ).all()
    )
    # 已作答 + 仍在错题本 = 本轮完整题集（答对会被移除，需并集还原）
    merged = list(dict.fromkeys(current_ids + answered_ids))
    return attempt, build_questions(db, merged, attempt.id)


def _attempt_question_ids(db: Session, attempt: QuizAttempt) -> list[int]:
    if attempt.kind == "daily":
        return _daily_word_ids(db, attempt.user_id, attempt.study_date)
    if attempt.kind == "archive":
        current_ids = _archive_question_ids(db, attempt.user_id)
    else:
        current_ids = wrong_word_service.wrong_word_ids(db, attempt.user_id)
    answered_ids = list(
        db.scalars(
            select(QuizAnswer.word_id).where(QuizAnswer.attempt_id == attempt.id)
        ).all()
    )
    return list(dict.fromkeys(current_ids + answered_ids))


def _archive_question_ids(db: Session, user_id: int) -> list[int]:
    """错题库专项练习的取题集合：优先错误次数多的，单轮上限 ARCHIVE_QUIZ_LIMIT。"""
    return wrong_word_service.archive_word_ids(
        db,
        user_id,
        limit=ARCHIVE_QUIZ_LIMIT,
        sort=wrong_word_service.SORT_COUNT,
    )


def _get_open_attempt(db: Session, user_id: int, attempt_id: int, kind: str) -> QuizAttempt:
    attempt = db.get(QuizAttempt, attempt_id)
    if attempt is None or attempt.user_id != user_id or attempt.kind != kind:
        raise AppError("attempt_not_found", status_code=404)
    if attempt.finished_at is not None:
        raise AppError("attempt_already_finished", status_code=409)
    return attempt


def _record_answer(
    db: Session, attempt: QuizAttempt, question_id: int, choice_index: int
) -> tuple[GeneratedQuestion, bool]:
    question_ids = _attempt_question_ids(db, attempt)
    if question_id not in question_ids:
        raise AppError("question_not_found", status_code=404)

    pool = _library_pool(db)
    word = db.get(Word, question_id)
    question = _build_question(word, pool, attempt.id)

    if not isinstance(choice_index, int) or not (
        0 <= choice_index < len(question.options)
    ):
        raise AppError("validation_error", status_code=422)

    is_correct = choice_index == question.correct_index

    existing = db.scalar(
        select(QuizAnswer).where(
            QuizAnswer.attempt_id == attempt.id, QuizAnswer.word_id == question_id
        )
    )
    if existing is None:
        db.add(
            QuizAnswer(
                attempt_id=attempt.id,
                word_id=question_id,
                question_type=question.question_type,
                choice_index=choice_index,
                is_correct=is_correct,
                answered_at=utcnow(),
            )
        )
    else:
        existing.question_type = question.question_type
        existing.choice_index = choice_index
        existing.is_correct = is_correct
        existing.answered_at = utcnow()

    return question, is_correct


def _open_daily_attempt(db: Session, user_id: int) -> QuizAttempt:
    attempt = db.scalar(
        select(QuizAttempt)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.kind == "daily",
            QuizAttempt.study_date == study_service.today_date(),
        )
        .order_by(QuizAttempt.id.desc())
    )
    if attempt is None:
        raise AppError("attempt_not_found", status_code=404)
    if attempt.finished_at is not None:
        raise AppError("attempt_already_finished", status_code=409)
    return attempt


def _open_review_attempt(db: Session, user_id: int) -> QuizAttempt:
    attempt = db.scalar(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id, QuizAttempt.kind == "review")
        .order_by(QuizAttempt.id.desc())
    )
    if attempt is None:
        raise AppError("attempt_not_found", status_code=404)
    if attempt.finished_at is not None:
        raise AppError("attempt_already_finished", status_code=409)
    return attempt


def _open_archive_attempt(db: Session, user_id: int) -> QuizAttempt:
    attempt = db.scalar(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id, QuizAttempt.kind == "archive")
        .order_by(QuizAttempt.id.desc())
    )
    if attempt is None:
        raise AppError("attempt_not_found", status_code=404)
    if attempt.finished_at is not None:
        raise AppError("attempt_already_finished", status_code=409)
    return attempt


def _archive_count(db: Session, user_id: int, word_id: int) -> int:
    row = db.scalar(
        select(WrongWordArchive).where(
            WrongWordArchive.user_id == user_id, WrongWordArchive.word_id == word_id
        )
    )
    return int(row.wrong_count) if row else 0


def record_daily_quiz_answer(
    db: Session, user_id: int, question_id: int, choice_index: int
) -> dict:
    """今日测验作答。

    答错 → 写入错题本（已存在则保留首次 ``added_at``、累加次数）并累加错题库；
    答对 → **不删除任何错题**（FR-026 / R-008）。
    """
    attempt = _open_daily_attempt(db, user_id)
    question, is_correct = _record_answer(db, attempt, question_id, choice_index)

    added_to_wrong_words = False
    if not is_correct:
        # 已存在 → 不新增、不改 added_at（FR-030），只累加次数并归零连续答对
        added_to_wrong_words = wrong_word_service.touch_wrong(
            db, user_id, question_id
        ).added_to_wrong_words

    db.commit()
    return {
        "question_id": question_id,
        "is_correct": is_correct,
        "correct_index": question.correct_index,
        "added_to_wrong_words": added_to_wrong_words,
    }


def record_review_answer(
    db: Session, user_id: int, question_id: int, choice_index: int
) -> dict:
    """错题专项练习作答。

    答对 → 连续答对次数 +1，达到 ``REVIEW_REMOVE_STREAK``（默认 2）才移出错题本
    （唯一移除路径）；未达阈值则保留，返回当前 streak 供前端提示"还差几次"。
    答错 → 连续答对归零、累加错误次数（已在册不改 ``added_at``，FR-037），
    并累加错题库。
    """
    attempt = _open_review_attempt(db, user_id)
    question, is_correct = _record_answer(db, attempt, question_id, choice_index)

    removed_from_wrong_words = False
    added_back_to_wrong_words = False
    correct_streak = 0
    if is_correct:
        wrong = db.scalar(
            select(WrongWord).where(
                WrongWord.user_id == user_id, WrongWord.word_id == question_id
            )
        )
        if wrong is not None:
            wrong.correct_streak = (wrong.correct_streak or 0) + 1
            if wrong.correct_streak >= REVIEW_REMOVE_STREAK:
                db.delete(wrong)  # 唯一的错题删除路径（FR-038）
                removed_from_wrong_words = True
            else:
                correct_streak = wrong.correct_streak
    else:
        # 答错：连续答对归零、次数累加；若本轮已因答对被移除 → 重新入本（FR-037）
        added_back_to_wrong_words = wrong_word_service.touch_wrong(
            db, user_id, question_id
        ).added_to_wrong_words

    db.commit()
    return {
        "question_id": question_id,
        "is_correct": is_correct,
        "correct_index": question.correct_index,
        "removed_from_wrong_words": removed_from_wrong_words,
        "added_back_to_wrong_words": added_back_to_wrong_words,
        "correct_streak": correct_streak,
    }


def start_archive_quiz(db: Session, user_id: int) -> tuple[QuizAttempt, list[GeneratedQuestion]]:
    """开启错题库专项练习：题目来自错题库（错误多的优先，单轮上限）；空 → 409。"""
    word_ids = wrong_word_service.archive_word_ids(db, user_id)
    if not word_ids:
        raise AppError("no_archive_words", status_code=409)

    attempt = _unfinished_attempt(db, user_id, "archive")
    if attempt is None:
        attempt = QuizAttempt(
            user_id=user_id,
            kind="archive",
            study_date=None,
            started_at=utcnow(),
            total_count=len(word_ids),
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

    merged = _attempt_question_ids(db, attempt)
    return attempt, build_questions(db, merged, attempt.id)


def record_archive_answer(
    db: Session, user_id: int, question_id: int, choice_index: int
) -> dict:
    """错题库专项练习作答。

    答对 → **不移除、不减次数**（错题库是永久档案）；
    答错 → 错题库次数 +1，同时确保该词在错题本中（待复习队列）。
    """
    attempt = _open_archive_attempt(db, user_id)
    question, is_correct = _record_answer(db, attempt, question_id, choice_index)

    added_to_wrong_words = False
    archive_wrong_count = 0
    if not is_correct:
        result = wrong_word_service.touch_wrong(db, user_id, question_id)
        added_to_wrong_words = result.added_to_wrong_words
        archive_wrong_count = result.archive_wrong_count
    else:
        archive_wrong_count = _archive_count(db, user_id, question_id)

    db.commit()
    return {
        "question_id": question_id,
        "is_correct": is_correct,
        "correct_index": question.correct_index,
        "removed_from_wrong_words": False,  # 错题库永不移除
        "added_to_wrong_words": added_to_wrong_words,
        "archive_wrong_count": archive_wrong_count,
    }


def _finish(db: Session, attempt: QuizAttempt) -> dict:
    answers = list(
        db.scalars(
            select(QuizAnswer).where(QuizAnswer.attempt_id == attempt.id)
        ).all()
    )
    total = len(answers)
    correct = sum(1 for answer in answers if answer.is_correct)
    wrong = total - correct
    accuracy = round(correct / total, 4) if total else 0.0
    duration = int((utcnow() - attempt.started_at).total_seconds())

    attempt.total_count = total
    attempt.correct_count = correct
    attempt.wrong_count = wrong
    attempt.finished_at = utcnow()
    db.commit()

    return {
        "attempt_id": attempt.id,
        "total_count": total,
        "correct_count": correct,
        "wrong_count": wrong,
        "accuracy": accuracy,
        "duration_seconds": duration,
        "wrong_word_ids": [answer.word_id for answer in answers if not answer.is_correct],
    }


def finish_daily_quiz(db: Session, user_id: int) -> dict:
    attempt = _open_daily_attempt(db, user_id)
    result = _finish(db, attempt)
    result["new_wrong_words"] = result.pop("wrong_word_ids")
    # 003：「当日测验完成」作为轮次完成信号（FR-004）—— 仅当本轮已覆盖时迁移为已完成；
    # 响应体字段不变，不新增错误码
    round_service.mark_completed(db, user_id)
    return result


def finish_review_quiz(db: Session, user_id: int) -> dict:
    attempt = _open_review_attempt(db, user_id)
    result = _finish(db, attempt)
    result.pop("wrong_word_ids")
    result["remaining_wrong_count"] = wrong_word_service.count_wrong_words(
        db, user_id
    )
    return result


def finish_archive_quiz(db: Session, user_id: int) -> dict:
    attempt = _open_archive_attempt(db, user_id)
    result = _finish(db, attempt)
    result.pop("wrong_word_ids")
    result["archive_total"] = wrong_word_service.count_archive_words(db, user_id)
    result["remaining_wrong_count"] = wrong_word_service.count_wrong_words(db, user_id)
    return result


def current_attempt_for_today(db: Session, user_id: int) -> QuizAttempt | None:
    return db.scalar(
        select(QuizAttempt).where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.kind == "daily",
            QuizAttempt.study_date == study_service.today_date(),
            QuizAttempt.finished_at.is_(None),
        )
    )


__all__ = [
    "ARCHIVE_QUIZ_LIMIT",
    "GeneratedQuestion",
    "REVIEW_REMOVE_STREAK",
    "build_questions",
    "current_attempt_for_today",
    "finish_archive_quiz",
    "finish_daily_quiz",
    "finish_review_quiz",
    "record_archive_answer",
    "record_daily_quiz_answer",
    "record_review_answer",
    "start_archive_quiz",
    "start_daily_quiz",
    "start_review_quiz",
]

# 便于测试引用默认目标值
DEFAULT_GOAL = settings.daily_goal_default
