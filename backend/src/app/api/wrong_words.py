"""错题本 / 错题库接口：只读列表（新增 / 删除只发生在测验作答路径）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.models.word import Word
from app.schemas.wrong_word import (
    WrongArchiveItem,
    WrongArchiveListResponse,
    WrongWordItem,
    WrongWordListResponse,
)
from app.services import wrong_word_service

router = APIRouter(prefix="/wrong-words", tags=["wrong-words"])


def _words_map(db: Session, word_ids: list[int]) -> dict[int, Word]:
    if not word_ids:
        return {}
    rows = db.scalars(select(Word).where(Word.id.in_(word_ids))).all()
    return {word.id: word for word in rows}


@router.get("", response_model=WrongWordListResponse)
def list_wrong_words(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WrongWordListResponse:
    rows, total = wrong_word_service.list_wrong_words(
        db, user.id, page=page, page_size=page_size
    )
    words = _words_map(db, [row.word_id for row in rows])

    items = []
    for row in rows:
        word = words.get(row.word_id)
        if word is None:
            continue
        items.append(
            WrongWordItem(
                word_id=row.word_id,
                spelling=word.spelling,
                meaning_zh=word.meaning_zh,
                phrase=word.phrase,
                phonetic=word.phonetic,
                added_at=row.added_at,
                wrong_count=row.wrong_count or 1,
                correct_streak=row.correct_streak or 0,
            )
        )

    return WrongWordListResponse(
        total=total, page=page, page_size=page_size, items=items
    )


@router.get("/archive", response_model=WrongArchiveListResponse)
def list_archive_words(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("added", pattern="^(added|count)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WrongArchiveListResponse:
    """错题库：永久档案，只返回错误次数，不返回时间（无时间字段）。"""
    rows, total = wrong_word_service.list_archive_words(
        db, user.id, page=page, page_size=page_size, sort=sort
    )
    words = _words_map(db, [row.word_id for row in rows])

    items = []
    for row in rows:
        word = words.get(row.word_id)
        if word is None:
            continue
        items.append(
            WrongArchiveItem(
                word_id=row.word_id,
                spelling=word.spelling,
                meaning_zh=word.meaning_zh,
                phrase=word.phrase,
                phonetic=word.phonetic,
                wrong_count=row.wrong_count or 1,
            )
        )

    return WrongArchiveListResponse(
        total=total, page=page, page_size=page_size, sort=sort, items=items
    )
