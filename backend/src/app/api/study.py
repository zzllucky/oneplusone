"""今日学习接口：集合、浏览标记、发音。"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.models.word import Word
from app.schemas.study import (
    StudyWordItem,
    TodayStudyResponse,
    ViewWordResponse,
)
from app.services import round_service, settings_service, study_service

router = APIRouter(prefix="/study", tags=["study"])


def _today_response(db: Session, user: User) -> TodayStudyResponse:
    goal = settings_service.get_daily_goal(db, user.id)
    # 取词范围由 services/round_service 的当前轮游标决定（003 循环学习）：
    # 本轮耗尽即自动开启新一轮；开启新轮与轮末补记的结构化日志由 round_service 输出
    study_service.get_or_create_today_set(db, user.id, goal)
    items = study_service.today_items(db, user.id)
    summary = study_service.today_summary(db, user.id, goal)

    words = {word.id: word for word in db.query(Word).all()} if items else {}
    payload = []
    for item in items:
        word = words.get(item.word_id)
        if word is None:
            continue
        payload.append(
            StudyWordItem(
                word_id=word.id,
                spelling=word.spelling,
                meaning_zh=word.meaning_zh,
                phrase=word.phrase,
                phonetic=word.phonetic,
                order_index=item.order_index,
                viewed_at=item.viewed_at,
            )
        )

    return TodayStudyResponse(
        study_date=summary.study_date.isoformat(),
        total_count=summary.total_count,
        viewed_count=summary.viewed_count,
        all_viewed=summary.all_viewed,
        quiz_unlocked=summary.quiz_unlocked,
        library_exhausted=summary.library_exhausted,
        items=payload,
        round=asdict(round_service.progress(db, user.id)),
    )


@router.get("/today", response_model=TodayStudyResponse)
def today(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> TodayStudyResponse:
    """首次访问即生成当日集合（数量 = min(每日目标, 未学单词数)）。"""
    return _today_response(db, user)


@router.post("/today/items/{word_id}/view", response_model=ViewWordResponse)
def view_word(
    word_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ViewWordResponse:
    _, summary, _ = study_service.mark_viewed(db, user.id, word_id)
    return ViewWordResponse(
        word_id=word_id,
        viewed_count=summary.viewed_count,
        total_count=summary.total_count,
        all_viewed=summary.all_viewed,
        quiz_unlocked=summary.quiz_unlocked,
    )


