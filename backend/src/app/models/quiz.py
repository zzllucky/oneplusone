"""quiz_attempts / quiz_answers —— 测验与专项练习轮次及作答明细。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('daily','review','archive')", name="ck_quiz_attempts_kind"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # kind='daily' 时有值；kind='review' 为 NULL
    study_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    # NULL = 进行中
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    answers: Mapped[list["QuizAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    __table_args__ = (
        CheckConstraint(
            "question_type IN ('en2zh','zh2en')", name="ck_quiz_answers_type"
        ),
        UniqueConstraint("attempt_id", "word_id", name="uq_attempt_word"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False
    )
    word_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("words.id"), nullable=False
    )
    question_type: Mapped[str] = mapped_column(String(8), nullable=False)
    choice_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    answered_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )

    attempt: Mapped[QuizAttempt] = relationship(back_populates="answers")
