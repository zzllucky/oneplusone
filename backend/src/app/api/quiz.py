"""测验接口：今日测验（需全部浏览解锁）与错题专项练习。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.quiz import (
    ArchiveAnswerResponse,
    ArchiveFinishResponse,
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizFinishResponse,
    QuizQuestionItem,
    QuizStartResponse,
    ReviewAnswerResponse,
    ReviewFinishResponse,
)
from app.services import quiz_service

router = APIRouter(prefix="/quiz", tags=["quiz"])


def _start_response(attempt, questions) -> QuizStartResponse:
    return QuizStartResponse(
        attempt_id=attempt.id,
        questions=[
            QuizQuestionItem(
                question_id=question.word_id,
                word_id=question.word_id,
                type=question.question_type,
                prompt=question.prompt,
                options=question.options,
            )
            for question in questions
        ],
    )


@router.post("/today/start", response_model=QuizStartResponse)
def start_today(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> QuizStartResponse:
    attempt, questions = quiz_service.start_daily_quiz(db, user.id)
    return _start_response(attempt, questions)


@router.post("/today/answer", response_model=QuizAnswerResponse)
def answer_today(
    payload: QuizAnswerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAnswerResponse:
    result = quiz_service.record_daily_quiz_answer(
        db, user.id, payload.question_id, payload.choice_index
    )
    return QuizAnswerResponse(**result)


@router.post("/today/finish", response_model=QuizFinishResponse)
def finish_today(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> QuizFinishResponse:
    return QuizFinishResponse(**quiz_service.finish_daily_quiz(db, user.id))


@router.post("/review/start", response_model=QuizStartResponse)
def start_review(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> QuizStartResponse:
    attempt, questions = quiz_service.start_review_quiz(db, user.id)
    return _start_response(attempt, questions)


@router.post("/review/answer", response_model=ReviewAnswerResponse)
def answer_review(
    payload: QuizAnswerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewAnswerResponse:
    result = quiz_service.record_review_answer(
        db, user.id, payload.question_id, payload.choice_index
    )
    return ReviewAnswerResponse(**result)


@router.post("/review/finish", response_model=ReviewFinishResponse)
def finish_review(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ReviewFinishResponse:
    return ReviewFinishResponse(**quiz_service.finish_review_quiz(db, user.id))


@router.post("/archive/start", response_model=QuizStartResponse)
def start_archive(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> QuizStartResponse:
    attempt, questions = quiz_service.start_archive_quiz(db, user.id)
    return _start_response(attempt, questions)


@router.post("/archive/answer", response_model=ArchiveAnswerResponse)
def answer_archive(
    payload: QuizAnswerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ArchiveAnswerResponse:
    result = quiz_service.record_archive_answer(
        db, user.id, payload.question_id, payload.choice_index
    )
    return ArchiveAnswerResponse(**result)


@router.post("/archive/finish", response_model=ArchiveFinishResponse)
def finish_archive(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ArchiveFinishResponse:
    return ArchiveFinishResponse(**quiz_service.finish_archive_quiz(db, user.id))
