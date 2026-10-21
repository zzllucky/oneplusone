"""语法学习服务：大纲 / 学卡 / 轮次 / 判分 / 语法错题本。

规则常量集中在本模块（前端不复制业务规则）：

- ``GRAMMAR_WRONG_REMOVE_STREAK`` —— 语法错题本移除所需的连续答对次数（FR-013）
- ``GRAMMAR_LEVELS`` —— 题库出题的层级递进顺序（FR-008，不洗牌）
- ``GRAMMAR_SOURCES`` —— 轮次来源（``card`` 卡内检测 / ``bank`` 题库练习）

本模块不触碰单词模块的任何表（FR-020）。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.logging import get_logger
from app.models.base import utcnow
from app.models.grammar import GrammarOption, GrammarPoint, GrammarQuestion
from app.models.grammar_progress import (
    GrammarAnswer,
    GrammarAttempt,
    GrammarPointProgress,
    GrammarWrongPoint,
)

GRAMMAR_WRONG_REMOVE_STREAK = 2
GRAMMAR_LEVELS = ("L1", "L2", "L3")
GRAMMAR_SOURCES = ("card", "bank")

# 结构化日志：只记用户标识与知识点标识，不记任何身份类信息（FR-022）
logger = get_logger("app.grammar")


def sanitize_payload(payload: dict) -> dict:
    """清洗教研内容：剔除答案与"猜一猜"选项反馈（FR-007）。

    ``grammar_points.payload`` 是教研原始 JSON，含 ``guess.answer`` 与
    ``guess.options[].feedback``（后者自带"对！/ 不对——"判词，同时下发即可
    反推正解），出库前必须清除。反馈改由 ``get_guess_feedback`` 在作答之后下发。
    """
    cleaned = _strip_answers(payload)
    guess = cleaned.get("guess")
    if isinstance(guess, dict) and isinstance(guess.get("options"), list):
        guess["options"] = [
            {"key": option.get("key"), "text": option.get("text")}
            for option in guess["options"]
            if isinstance(option, dict)
        ]
    return cleaned


def _strip_answers(node):
    """递归删除 ``answer`` / ``is_correct`` / ``correct_key`` 键。"""
    if isinstance(node, dict):
        return {
            key: _strip_answers(value)
            for key, value in node.items()
            if key not in ("answer", "is_correct", "correct_key")
        }
    if isinstance(node, list):
        return [_strip_answers(item) for item in node]
    return node


def list_outline(db: Session, user_id: int) -> dict:
    """语法大纲：按模块分组 + 当前用户状态 + 汇总计数（FR-001/002/003）。

    一次查询知识点全表，再分别取该用户的进度与错题本、各知识点 ``source='bank'``
    的题数；无进度时状态为 ``not_started``。
    """
    points = list(
        db.scalars(
            select(GrammarPoint).order_by(
                GrammarPoint.module, GrammarPoint.order_index, GrammarPoint.id
            )
        ).all()
    )
    progresses = {
        row.point_id: row
        for row in db.scalars(
            select(GrammarPointProgress).where(GrammarPointProgress.user_id == user_id)
        ).all()
    }
    wrong_ids = {
        row[0]
        for row in db.execute(
            select(GrammarWrongPoint.point_id).where(
                GrammarWrongPoint.user_id == user_id
            )
        ).all()
    }
    bank_counts = dict(
        db.execute(
            select(GrammarQuestion.point_id, func.count())
            .where(GrammarQuestion.source == "bank")
            .group_by(GrammarQuestion.point_id)
        ).all()
    )

    # 分组键为 (module, module_name)：同一字母下有多个模块（如 T 下 8 个时态、
    # F 下不定式与动名词），只按 module 分组会把它们合并且组名取首个
    modules: dict[tuple[str, str], dict] = {}
    for point in points:
        module = modules.setdefault(
            (point.module, point.module_name),
            {"module": point.module, "module_name": point.module_name, "points": []},
        )
        progress = progresses.get(point.id)
        module["points"].append(
            {
                "id": point.id,
                "title": point.title,
                "depth": point.depth,
                "card_type": point.card_type,
                "status": progress.status if progress else "not_started",
                "has_wrong": point.id in wrong_ids,
                "question_count": int(bank_counts.get(point.id, 0)),
            }
        )

    return {
        "total_points": len(points),
        "mastered_count": sum(
            1 for row in progresses.values() if row.status == "mastered"
        ),
        "wrong_count": sum(
            1 for point in points if point.id in wrong_ids
        ),
        "modules": [modules[key] for key in sorted(modules)],
    }


def _get_point(db: Session, point_id: str) -> GrammarPoint:
    point = db.get(GrammarPoint, point_id)
    if point is None:
        raise AppError("grammar_point_not_found", status_code=404)
    return point


def _progress(db: Session, user_id: int, point_id: str) -> GrammarPointProgress | None:
    return db.scalar(
        select(GrammarPointProgress).where(
            GrammarPointProgress.user_id == user_id,
            GrammarPointProgress.point_id == point_id,
        )
    )


def _has_wrong(db: Session, user_id: int, point_id: str) -> bool:
    return (
        db.scalar(
            select(GrammarWrongPoint.id).where(
                GrammarWrongPoint.user_id == user_id,
                GrammarWrongPoint.point_id == point_id,
            )
        )
        is not None
    )


def question_payloads(questions) -> list[dict]:
    """题目 → 下发结构（仅题干与选项 key/text，FR-007）。"""
    result = []
    for question in questions:
        options = [
            {"key": option.key, "text": option.text}
            for option in sorted(question.options, key=lambda row: row.order_index)
        ]
        result.append(
            {
                "question_id": question.id,
                "level": question.level,
                "stem": question.stem,
                "options": options,
            }
        )
    return result


def get_point_card(db: Session, user_id: int, point_id: str) -> dict:
    """知识点学卡：头部信息 + 清洗后的教研内容 + 卡内检测题（FR-004/FR-007）。"""
    point = _get_point(db, point_id)
    progress = _progress(db, user_id, point_id)
    questions = list(
        db.scalars(
            select(GrammarQuestion)
            .where(
                GrammarQuestion.point_id == point_id,
                GrammarQuestion.source == "card",
            )
            .order_by(GrammarQuestion.level, GrammarQuestion.order_index)
        ).all()
    )

    return {
        "point": {
            "id": point.id,
            "module": point.module,
            "module_name": point.module_name,
            "title": point.title,
            "depth": point.depth,
            "card_type": point.card_type,
            "status": progress.status if progress else "not_started",
            "has_wrong": _has_wrong(db, user_id, point_id),
        },
        "payload": sanitize_payload(point.payload),
        "check_questions": question_payloads(questions),
    }


def get_guess_feedback(db: Session, point_id: str, choice_key: str) -> str:
    """取"猜一猜"所选选项的反馈（作答之后才下发，FR-007）。

    不写库、不判分、不影响掌握状态；键不匹配 → 422 `invalid_choice_key`。
    """
    point = _get_point(db, point_id)
    options = (point.payload or {}).get("guess", {}).get("options", [])
    for option in options:
        if option.get("key") == choice_key:
            return option.get("feedback") or ""
    raise AppError("invalid_choice_key", status_code=422)


def mark_viewed(db: Session, user_id: int, point_id: str) -> dict:
    """标记已学：首次置 ``learning``；已是 ``mastered`` 不降级（幂等）。"""
    _get_point(db, point_id)
    row = _progress(db, user_id, point_id)
    now = utcnow()

    if row is None:
        row = GrammarPointProgress(
            user_id=user_id,
            point_id=point_id,
            status="learning",
            check_total=0,
            check_correct=0,
            studied_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        if row.status == "not_started":
            row.status = "learning"
        if row.studied_at is None:
            row.studied_at = now
        row.updated_at = now

    db.commit()
    db.refresh(row)
    return {
        "point_id": point_id,
        "status": row.status,
        "studied_at": row.studied_at,
    }


def start_attempt(
    db: Session,
    user_id: int,
    point_id: str,
    source: str = "card",
    level: str | None = None,
) -> tuple[GrammarAttempt, list[GrammarQuestion]]:
    """开启一轮学后检测（``card``）或题库练习（``bank``）。

    取题按层级递进 + 顺序（不洗牌，FR-008）；无题 → 409 `no_grammar_questions`。
    每次调用都新建轮次：中途退出后再次发起不恢复上一轮（US3-AC4）。
    """
    if source not in GRAMMAR_SOURCES:
        raise AppError("validation_error", status_code=422)
    if level is not None and level not in GRAMMAR_LEVELS:
        raise AppError("validation_error", status_code=422)

    _get_point(db, point_id)
    statement = select(GrammarQuestion).where(
        GrammarQuestion.point_id == point_id, GrammarQuestion.source == source
    )
    if level is not None:
        statement = statement.where(GrammarQuestion.level == level)
    questions = list(
        db.scalars(
            statement.order_by(GrammarQuestion.level, GrammarQuestion.order_index)
        ).all()
    )
    if not questions:
        raise AppError("no_grammar_questions", status_code=409)

    attempt = GrammarAttempt(
        user_id=user_id,
        point_id=point_id,
        source=source,
        level=level,
        total_count=len(questions),
        correct_count=0,
        wrong_count=0,
        started_at=utcnow(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    logger.info(
        "语法轮次开始 user_id=%s point_id=%s source=%s level=%s count=%s attempt_id=%s",
        user_id,
        point_id,
        source,
        level,
        len(questions),
        attempt.id,
    )
    return attempt, questions


def _attempt_counts(db: Session, attempt: GrammarAttempt) -> dict:
    answers = list(
        db.scalars(
            select(GrammarAnswer).where(GrammarAnswer.attempt_id == attempt.id)
        ).all()
    )
    correct = sum(1 for answer in answers if answer.is_correct)
    answered = len(answers)
    return {
        "total_count": attempt.total_count,
        "answered_count": answered,
        "correct_count": correct,
        "wrong_count": answered - correct,
    }


def _answer_result(
    db: Session,
    attempt: GrammarAttempt,
    question: GrammarQuestion,
    choice_key: str,
    is_correct: bool,
    *,
    added: bool,
    removed: bool,
    streak: int,
) -> dict:
    correct_option = next(row for row in question.options if row.is_correct)
    chosen = next((row for row in question.options if row.key == choice_key), None)
    return {
        "question_id": question.id,
        "is_correct": is_correct,
        "correct_key": correct_option.key,
        "explanation": question.explanation,
        # 答错给出所选错项的错因；答对为 null（FR-005/FR-009）
        "feedback": None if is_correct else (chosen.feedback if chosen else None),
        "attempt": _attempt_counts(db, attempt),
        "added_to_wrong_points": added,
        "removed_from_wrong_points": removed,
        "correct_streak": streak,
    }


def _touch_wrong_point(db: Session, user_id: int, point_id: str) -> bool:
    """答错：不存在则插入，存在则累加次数并归零连续答对（FR-012）。"""
    row = db.scalar(
        select(GrammarWrongPoint).where(
            GrammarWrongPoint.user_id == user_id,
            GrammarWrongPoint.point_id == point_id,
        )
    )
    now = utcnow()
    if row is None:
        db.add(
            GrammarWrongPoint(
                user_id=user_id,
                point_id=point_id,
                wrong_count=1,
                correct_streak=0,
                added_at=now,
                last_wrong_at=now,
            )
        )
        return True
    row.wrong_count = (row.wrong_count or 0) + 1
    row.correct_streak = 0
    row.last_wrong_at = now
    return False


def _reward_correct(db: Session, user_id: int, point_id: str) -> tuple[bool, int]:
    """答对：连续答对 +1，达到阈值删除条目（FR-013，唯一移除路径）。"""
    row = db.scalar(
        select(GrammarWrongPoint).where(
            GrammarWrongPoint.user_id == user_id,
            GrammarWrongPoint.point_id == point_id,
        )
    )
    if row is None:
        return False, 0
    row.correct_streak = (row.correct_streak or 0) + 1
    if row.correct_streak >= GRAMMAR_WRONG_REMOVE_STREAK:
        streak = row.correct_streak
        db.delete(row)
        return True, streak
    return False, row.correct_streak


def record_answer(
    db: Session, user_id: int, attempt_id: int, question_id: str, choice_key: str
) -> dict:
    """判分：一次事务内写作答 → 更新轮次计数 → 维护语法错题本（FR-009/012/013/015）。"""
    attempt = db.get(GrammarAttempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise AppError("grammar_attempt_not_found", status_code=404)
    if attempt.finished_at is not None:
        raise AppError("grammar_attempt_already_finished", status_code=409)

    question = db.get(GrammarQuestion, question_id)
    if question is None or question.point_id != attempt.point_id:
        raise AppError("grammar_question_not_found", status_code=404)

    keys = {option.key for option in question.options}
    if choice_key not in keys:
        raise AppError("invalid_choice_key", status_code=422)

    existing = db.scalar(
        select(GrammarAnswer).where(
            GrammarAnswer.attempt_id == attempt_id,
            GrammarAnswer.question_id == question_id,
        )
    )
    if existing is not None:
        # 同一轮同一题重复提交：返回首次结果，不重复计分（FR-015）
        return _answer_result(
            db,
            attempt,
            question,
            existing.choice_key,
            existing.is_correct,
            added=False,
            removed=False,
            streak=0,
        )

    chosen = next(row for row in question.options if row.key == choice_key)
    is_correct = bool(chosen.is_correct)
    db.add(
        GrammarAnswer(
            attempt_id=attempt_id,
            question_id=question_id,
            choice_key=choice_key,
            is_correct=is_correct,
            answered_at=utcnow(),
        )
    )

    tag = question.error_tag or question.point_id
    added = False
    removed = False
    streak = 0
    if is_correct:
        removed, streak = _reward_correct(db, user_id, tag)
        if removed:
            logger.info("语法错题本移出 user_id=%s point_id=%s", user_id, tag)
    else:
        added = _touch_wrong_point(db, user_id, tag)
        if added:
            logger.info("语法错题本新增 user_id=%s point_id=%s", user_id, tag)
    logger.info(
        "语法判分 user_id=%s point_id=%s question_id=%s correct=%s attempt_id=%s",
        user_id,
        question.point_id,
        question.id,
        is_correct,
        attempt_id,
    )

    counts = _attempt_counts(db, attempt)
    attempt.correct_count = counts["correct_count"]
    attempt.wrong_count = counts["wrong_count"]
    db.commit()

    return _answer_result(
        db,
        attempt,
        question,
        choice_key,
        is_correct,
        added=added,
        removed=removed,
        streak=streak,
    )


def finish_attempt(db: Session, user_id: int, attempt_id: int) -> dict:
    """结算：回填计数与用时；``card`` 轮次全对才判定掌握（FR-006/FR-010/FR-016）。"""
    attempt = db.get(GrammarAttempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise AppError("grammar_attempt_not_found", status_code=404)
    if attempt.finished_at is not None:
        raise AppError("grammar_attempt_already_finished", status_code=409)

    answers = list(
        db.scalars(
            select(GrammarAnswer).where(GrammarAnswer.attempt_id == attempt.id)
        ).all()
    )
    total = attempt.total_count
    correct = sum(1 for answer in answers if answer.is_correct)
    wrong = len(answers) - correct
    accuracy = round(correct / total, 4) if total else 0.0
    now = utcnow()
    duration = int((now - attempt.started_at).total_seconds())

    attempt.correct_count = correct
    attempt.wrong_count = wrong
    attempt.finished_at = now

    # 掌握只由 card 轮次推进（R-002）；练习不改变状态
    mastered = attempt.source == "card" and total > 0 and correct == total
    status = "not_started"
    if attempt.source == "card":
        row = _progress(db, user_id, attempt.point_id)
        if row is None:
            row = GrammarPointProgress(
                user_id=user_id,
                point_id=attempt.point_id,
                status="learning",
                studied_at=now,
                updated_at=now,
            )
            db.add(row)
        row.check_total = (row.check_total or 0) + len(answers)
        row.check_correct = (row.check_correct or 0) + correct
        row.updated_at = now
        if mastered:
            row.status = "mastered"
            if row.mastered_at is None:
                row.mastered_at = now
        elif row.status == "not_started":
            row.status = "learning"
        status = row.status
    else:
        row = _progress(db, user_id, attempt.point_id)
        status = row.status if row else "not_started"

    db.commit()
    logger.info(
        "语法轮次结算 user_id=%s point_id=%s attempt_id=%s correct=%s/%s mastered=%s",
        user_id,
        attempt.point_id,
        attempt.id,
        correct,
        total,
        mastered,
    )
    return {
        "attempt_id": attempt.id,
        "source": attempt.source,
        "point_id": attempt.point_id,
        "total_count": total,
        "correct_count": correct,
        "wrong_count": wrong,
        "accuracy": accuracy,
        "duration_seconds": duration,
        "mastered": mastered,
        "status": status,
    }


def list_wrong_points(db: Session, user_id: int) -> dict:
    """语法错题本：按加入时间升序（与单词错题本一致），补模块与标题（FR-014）。"""
    rows = list(
        db.execute(
            select(GrammarWrongPoint, GrammarPoint)
            .join(GrammarPoint, GrammarPoint.id == GrammarWrongPoint.point_id)
            .where(GrammarWrongPoint.user_id == user_id)
            .order_by(GrammarWrongPoint.added_at, GrammarWrongPoint.id)
        ).all()
    )
    items = [
        {
            "point_id": wrong.point_id,
            "title": point.title,
            "module": point.module,
            "module_name": point.module_name,
            "wrong_count": wrong.wrong_count,
            "correct_streak": wrong.correct_streak,
            "added_at": wrong.added_at,
            "last_wrong_at": wrong.last_wrong_at,
        }
        for wrong, point in rows
    ]
    return {"total": len(items), "items": items}


__all__ = [
    "GRAMMAR_LEVELS",
    "GRAMMAR_SOURCES",
    "GRAMMAR_WRONG_REMOVE_STREAK",
    "finish_attempt",
    "get_guess_feedback",
    "get_point_card",
    "list_outline",
    "list_wrong_points",
    "mark_viewed",
    "question_payloads",
    "record_answer",
    "sanitize_payload",
    "start_attempt",
]
