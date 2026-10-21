"""语法接口：大纲 / 学卡 / 检测与练习 / 语法错题本。

全部端点需登录态（FR-018）；字段与错误码以
specs/006-grammar-study/contracts/api.md 为唯一契约来源。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.grammar import (
    AttemptStartResponse,
    GrammarAnswerRequest,
    GrammarAnswerResponse,
    GrammarFinishResponse,
    GrammarGuessRequest,
    GrammarGuessResponse,
    GrammarOutlineResponse,
    GrammarPointDetailResponse,
    GrammarPracticeStartRequest,
    GrammarViewResponse,
    GrammarWrongPointListResponse,
)
from app.services import grammar_service

router = APIRouter(prefix="/grammar", tags=["grammar"])


@router.get("/outline", response_model=GrammarOutlineResponse)
def get_outline(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> GrammarOutlineResponse:
    """语法大纲：模块分组 + 掌握状态 + 汇总计数。"""
    return GrammarOutlineResponse(**grammar_service.list_outline(db, user.id))


@router.get("/points/{point_id}", response_model=GrammarPointDetailResponse)
def get_point(
    point_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GrammarPointDetailResponse:
    """知识点学卡：教研内容（已清洗）+ 卡内检测题。"""
    return GrammarPointDetailResponse(**grammar_service.get_point_card(db, user.id, point_id))


@router.post("/points/{point_id}/view", response_model=GrammarViewResponse)
def view_point(
    point_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GrammarViewResponse:
    """标记已学（幂等）：首次置为学习中，已掌握不降级。"""
    return GrammarViewResponse(**grammar_service.mark_viewed(db, user.id, point_id))


@router.post("/points/{point_id}/guess", response_model=GrammarGuessResponse)
def guess_point(
    point_id: str,
    payload: GrammarGuessRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GrammarGuessResponse:
    """猜一猜反馈：作答之后按所选键下发，不泄露正解。"""
    feedback = grammar_service.get_guess_feedback(db, point_id, payload.choice_key)
    return GrammarGuessResponse(
        point_id=point_id, choice_key=payload.choice_key, feedback=feedback
    )


@router.post("/points/{point_id}/check/start", response_model=AttemptStartResponse)
def start_check(
    point_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptStartResponse:
    """开始学后检测（卡内题目）。"""
    attempt, questions = grammar_service.start_attempt(
        db, user.id, point_id, source="card"
    )
    return _start_response(attempt, questions)


@router.post("/points/{point_id}/practice/start", response_model=AttemptStartResponse)
def start_practice(
    point_id: str,
    payload: GrammarPracticeStartRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptStartResponse:
    """开始题库练习：按 L1 → L2 → L3 递进出题。"""
    level = payload.level if payload else None
    attempt, questions = grammar_service.start_attempt(
        db, user.id, point_id, source="bank", level=level
    )
    return _start_response(attempt, questions)


@router.post("/attempts/{attempt_id}/answer", response_model=GrammarAnswerResponse)
def answer_question(
    attempt_id: int,
    payload: GrammarAnswerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GrammarAnswerResponse:
    """作答并即时判分（学后检测与练习共用）。"""
    result = grammar_service.record_answer(
        db, user.id, attempt_id, payload.question_id, payload.choice_key
    )
    return GrammarAnswerResponse(**result)


@router.post("/attempts/{attempt_id}/finish", response_model=GrammarFinishResponse)
def finish_attempt(
    attempt_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GrammarFinishResponse:
    """结算本轮：正确率、用时与掌握判定。"""
    return GrammarFinishResponse(**grammar_service.finish_attempt(db, user.id, attempt_id))


@router.get("/wrong-points", response_model=GrammarWrongPointListResponse)
def list_wrong_points(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> GrammarWrongPointListResponse:
    """语法错题本：按加入时间升序，可直达学卡重学。"""
    return GrammarWrongPointListResponse(**grammar_service.list_wrong_points(db, user.id))


def _start_response(attempt, questions) -> AttemptStartResponse:
    return AttemptStartResponse(
        attempt_id=attempt.id,
        source=attempt.source,
        point_id=attempt.point_id,
        questions=grammar_service.question_payloads(questions),
    )
