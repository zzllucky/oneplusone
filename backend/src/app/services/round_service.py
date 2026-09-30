"""轮次服务：当前轮维护、游标取词、覆盖 / 完成判定、补记与进度。

职责边界（章程 I）：
- 本模块**唯一**负责轮次状态迁移与取词范围；
- ``study_service`` 只消费"本轮待分配单词"，``quiz_service`` 只发"当日测验完成"信号；
- **不删除任何历史数据**（FR-008，由 T027 审计固化）。

补记（FR-014）发生在**轮次读取的统一入口**：``ensure_open_round`` / ``progress``
内部都会先执行 ``settle_pending_rounds``，因此首页（只看不分配）与学习页（分配）
在任何时序下都看到同一轮数（SC-006）。
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.base import utcnow
from app.models.study_round import StudyRound
from app.models.word import Word
from app.services import study_service

logger = logging.getLogger(__name__)


@dataclass
class RoundProgress:
    round_no: int
    learned_count: int
    total_count: int
    pending_quiz: bool


def _today() -> dt.date:
    """复用学习服务的"当日"口径（服务端统一时区）。"""
    return study_service.today_date()


def _local_date(moment: dt.datetime) -> dt.date:
    return (
        moment.replace(tzinfo=dt.timezone.utc)
        .astimezone(ZoneInfo(settings.timezone))
        .date()
    )


def _min_word_id(db: Session) -> int | None:
    return db.scalar(select(func.min(Word.id)))


def _max_word_id(db: Session) -> int | None:
    return db.scalar(select(func.max(Word.id)))


def _count_words(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Word)) or 0


def _open_round(db: Session, user_id: int) -> StudyRound | None:
    return db.scalar(
        select(StudyRound).where(
            StudyRound.user_id == user_id, StudyRound.completed_at.is_(None)
        )
    )


def settle_pending_rounds(db: Session, user_id: int) -> int:
    """补记（FR-014）：已覆盖但覆盖日已早于今天的轮次 → 记为已完成。

    只改轮次计数，**不为该日伪造任何测验成绩**。返回补记的轮次数。
    """
    today = _today()
    pending = list(
        db.scalars(
            select(StudyRound).where(
                StudyRound.user_id == user_id,
                StudyRound.completed_at.is_(None),
                StudyRound.covered_at.is_not(None),
            )
        ).all()
    )
    settled = 0
    for round_ in pending:
        if round_.covered_at is None:
            continue
        if _local_date(round_.covered_at) < today:
            round_.completed_at = utcnow()
            settled += 1
            logger.info(
                "study_round.settled",
                extra={
                    "user_id": user_id,
                    "round_no": round_.round_no,
                    "covered_at": round_.covered_at.isoformat(),
                },
            )
    if settled:
        db.commit()
    return settled


def ensure_open_round(db: Session, user_id: int) -> StudyRound:
    """返回当前进行中的轮次；不存在则惰性创建（补记在前）。"""
    settle_pending_rounds(db, user_id)
    round_ = _open_round(db, user_id)
    if round_ is not None:
        return round_

    start_cursor = _min_word_id(db) or 1
    max_no = db.scalar(
        select(func.max(StudyRound.round_no)).where(StudyRound.user_id == user_id)
    )
    round_ = StudyRound(
        user_id=user_id,
        round_no=(max_no or 0) + 1,
        cursor_word_id=start_cursor,
        started_on=_today(),
    )
    db.add(round_)
    db.commit()
    db.refresh(round_)
    logger.info(
        "study_round.created",
        extra={"user_id": user_id, "round_no": round_.round_no},
    )
    return round_


def allocate_word_ids(db: Session, user_id: int, goal: int) -> list[int]:
    """按当前轮游标取词（词库原顺序），不足目标时只返回剩余部分（FR-009）。"""
    if goal <= 0:
        return []
    round_ = ensure_open_round(db, user_id)
    return list(
        db.scalars(
            select(Word.id)
            .where(Word.id >= round_.cursor_word_id)
            .order_by(Word.id)
            .limit(goal)
        ).all()
    )


def advance_cursor(db: Session, user_id: int, allocated_ids: list[int]) -> None:
    """分配落库后推进游标；越过词库最后一个单词即标记"已覆盖"。"""
    if not allocated_ids:
        return
    round_ = _open_round(db, user_id)
    if round_ is None:
        return

    round_.cursor_word_id = max(allocated_ids) + 1
    max_id = _max_word_id(db)
    if max_id is None or round_.cursor_word_id > max_id:
        mark_covered(db, user_id, round_=round_)
    db.commit()


def rewind_cursor(db: Session, user_id: int, word_ids: list[int]) -> None:
    """回退游标到被撤销的一批单词之前（改每日目标重算当日集合时使用）。

    重算后当日集合可能变长或变短，游标必须回到这批单词的起点重新分配，
    否则被撤销的单词会被跳过；若此前已标记"已覆盖"，一并取消。
    """
    if not word_ids:
        return
    round_ = _open_round(db, user_id)
    if round_ is None:
        return
    round_.cursor_word_id = min(word_ids)
    if round_.covered_at is not None:
        round_.covered_at = None
    db.commit()


def mark_covered(db: Session, user_id: int, round_: StudyRound | None = None) -> bool:
    """标记本轮"已覆盖"（游标越过词库末尾）。已完成判定仍等测验信号。"""
    round_ = round_ or _open_round(db, user_id)
    if round_ is None or round_.covered_at is not None:
        return False
    round_.covered_at = utcnow()
    db.commit()
    logger.info(
        "study_round.covered",
        extra={"user_id": user_id, "round_no": round_.round_no},
    )
    return True


def mark_completed(db: Session, user_id: int) -> bool:
    """"当日测验完成"信号：仅在已覆盖时把轮次迁移为已完成（FR-004）。"""
    round_ = _open_round(db, user_id)
    if round_ is None or round_.covered_at is None or round_.completed_at is not None:
        return False
    round_.completed_at = utcnow()
    db.commit()
    logger.info(
        "study_round.completed",
        extra={"user_id": user_id, "round_no": round_.round_no},
    )
    return True


def completed_rounds(db: Session, user_id: int) -> int:
    settle_pending_rounds(db, user_id)
    return (
        db.scalar(
            select(func.count())
            .select_from(StudyRound)
            .where(
                StudyRound.user_id == user_id, StudyRound.completed_at.is_not(None)
            )
        )
        or 0
    )


def remaining_in_round(db: Session, user_id: int) -> int:
    """当前轮剩余未分配单词数（供 library_exhausted 新语义使用）。"""
    round_ = _open_round(db, user_id)
    if round_ is None:
        return _count_words(db)
    return (
        db.scalar(
            select(func.count())
            .select_from(Word)
            .where(Word.id >= round_.cursor_word_id)
        )
        or 0
    )


def progress(db: Session, user_id: int) -> RoundProgress:
    """当前轮进度（FR-006）；补记与惰性创建都在此统一触发。"""
    round_ = ensure_open_round(db, user_id)
    return RoundProgress(
        round_no=round_.round_no,
        learned_count=(
            db.scalar(
                select(func.count())
                .select_from(Word)
                .where(Word.id < round_.cursor_word_id)
            )
            or 0
        ),
        total_count=_count_words(db),
        pending_quiz=round_.covered_at is not None and round_.completed_at is None,
    )


__all__ = [
    "RoundProgress",
    "advance_cursor",
    "allocate_word_ids",
    "completed_rounds",
    "ensure_open_round",
    "mark_completed",
    "mark_covered",
    "progress",
    "remaining_in_round",
    "rewind_cursor",
    "settle_pending_rounds",
]
