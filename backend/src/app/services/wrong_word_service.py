"""错题本与错题库服务。

两块数据分工：
- ``wrong_words``（错题本）：待复习队列。答错入本、专项练习连续答对
  ``quiz_service.REVIEW_REMOVE_STREAK`` 次后移出（全项目唯一删除路径）。
- ``wrong_word_archive``（错题库）：永久档案。只累计错误次数，**不记录时间、
  永不移除**，与错题本是否清空无关。

本模块提供两块的读取；写入统一走 ``touch_wrong``（仅在答错路径调用）。
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.word import Word
from app.models.wrong_word import WrongWord
from app.models.wrong_word_archive import WrongWordArchive

# 列表排序方式：added = 加入顺序，count = 错误次数多的在前
SORT_ADDED = "added"
SORT_COUNT = "count"


@dataclass
class TouchResult:
    """一次答错的写入结果。"""

    added_to_wrong_words: bool  # 是否新入错题本（原本不在本中）
    archive_wrong_count: int  # 错题库中该词累计错误次数


def count_wrong_words(db: Session, user_id: int) -> int:
    return int(
        db.scalar(select(func.count(WrongWord.id)).where(WrongWord.user_id == user_id))
        or 0
    )


def count_archive_words(db: Session, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(WrongWordArchive.id)).where(
                WrongWordArchive.user_id == user_id
            )
        )
        or 0
    )


def list_wrong_words(
    db: Session, user_id: int, *, page: int = 1, page_size: int = 20
) -> tuple[list[WrongWord], int]:
    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)

    total = count_wrong_words(db, user_id)
    rows = list(
        db.scalars(
            select(WrongWord)
            .where(WrongWord.user_id == user_id)
            .order_by(WrongWord.added_at.asc(), WrongWord.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def list_archive_words(
    db: Session,
    user_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
    sort: str = SORT_ADDED,
) -> tuple[list[WrongWordArchive], int]:
    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)

    order_by = (
        (WrongWordArchive.wrong_count.desc(), WrongWordArchive.id.asc())
        if sort == SORT_COUNT
        else (WrongWordArchive.id.asc(),)
    )

    total = count_archive_words(db, user_id)
    rows = list(
        db.scalars(
            select(WrongWordArchive)
            .where(WrongWordArchive.user_id == user_id)
            .order_by(*order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def wrong_word_ids(db: Session, user_id: int) -> list[int]:
    return list(
        db.scalars(
            select(WrongWord.word_id)
            .where(WrongWord.user_id == user_id)
            .order_by(WrongWord.added_at.asc(), WrongWord.id.asc())
        ).all()
    )


def archive_word_ids(
    db: Session, user_id: int, *, limit: int | None = None, sort: str = SORT_ADDED
) -> list[int]:
    """错题库单词 id；``limit`` 用于限制单轮练习题量。"""
    order_by = (
        (WrongWordArchive.wrong_count.desc(), WrongWordArchive.id.asc())
        if sort == SORT_COUNT
        else (WrongWordArchive.id.asc(),)
    )
    statement = (
        select(WrongWordArchive.word_id)
        .where(WrongWordArchive.user_id == user_id)
        .order_by(*order_by)
    )
    if limit:
        statement = statement.limit(limit)
    return list(db.scalars(statement).all())


def touch_wrong(db: Session, user_id: int, word_id: int) -> TouchResult:
    """记录一次答错：错题本入本/累加，错题库永久累加。

    - 错题本：新入本保留首次 ``added_at``；已在册则累加次数、连续答对归零。
    - 错题库：无论错题本状态如何都累加，**永不删除**。
    """
    now = utcnow()

    row = db.scalar(
        select(WrongWord).where(
            WrongWord.user_id == user_id, WrongWord.word_id == word_id
        )
    )
    added = False
    if row is None:
        db.add(
            WrongWord(
                user_id=user_id,
                word_id=word_id,
                added_at=now,
                wrong_count=1,
                correct_streak=0,
                last_wrong_at=now,
            )
        )
        added = True
    else:
        row.wrong_count = (row.wrong_count or 0) + 1
        row.correct_streak = 0
        row.last_wrong_at = now

    archive = db.scalar(
        select(WrongWordArchive).where(
            WrongWordArchive.user_id == user_id, WrongWordArchive.word_id == word_id
        )
    )
    if archive is None:
        archive = WrongWordArchive(user_id=user_id, word_id=word_id, wrong_count=1)
        db.add(archive)
        db.flush()
    else:
        archive.wrong_count = (archive.wrong_count or 0) + 1

    return TouchResult(
        added_to_wrong_words=added, archive_wrong_count=archive.wrong_count
    )


def get_word(db: Session, word_id: int) -> Word | None:
    return db.get(Word, word_id)
