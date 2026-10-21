"""语法学习记录层：掌握进度 / 轮次 / 作答 / 语法错题本。

四张表全部按 ``user_id`` 隔离，与单词模块的表无任何关联（FR-020）。
内容与约束以 specs/006-grammar-study/data-model.md 为准。
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class GrammarPointProgress(Base):
    """知识点掌握进度：一名学生 × 一个知识点一条。

    状态只由学后检测推进（R-002）：打开学卡 → ``learning``；
    ``source='card'`` 轮次全对 → ``mastered``；练习结果不改本表。
    """

    __tablename__ = "grammar_point_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "point_id", name="uq_grammar_point_progress"),
        Index("ix_grammar_point_progress_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    point_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("grammar_points.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="not_started")
    check_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    check_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    studied_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    mastered_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )


class GrammarAttempt(Base):
    """轮次：一次学后检测（``card``）或一次题库练习（``bank``）。

    ``finished_at IS NULL`` 表示进行中；非空即已结束，拒绝再作答 / 再结算。
    """

    __tablename__ = "grammar_attempts"
    __table_args__ = (
        Index("ix_grammar_attempts_user_point", "user_id", "point_id"),
        Index("ix_grammar_attempts_user_started", "user_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    point_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("grammar_points.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(8), nullable=False)
    level: Mapped[str | None] = mapped_column(String(2), nullable=True)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)


class GrammarAnswer(Base):
    """作答记录：一轮内一题仅一条（重复提交以首次为准，FR-015）。"""

    __tablename__ = "grammar_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_grammar_answer"),
        Index("ix_grammar_answers_question_id", "question_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("grammar_attempts.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("grammar_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    choice_key: Mapped[str] = mapped_column(String(2), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answered_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )


class GrammarWrongPoint(Base):
    """语法错题本：一名学生 × 一个知识点一条。

    答错插入 / 累加，连续答对 ``GRAMMAR_WRONG_REMOVE_STREAK`` 次后删除
    （唯一移除路径，FR-013）。
    """

    __tablename__ = "grammar_wrong_points"
    __table_args__ = (
        UniqueConstraint("user_id", "point_id", name="uq_grammar_wrong_point"),
        Index("ix_grammar_wrong_points_user_added", "user_id", "added_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    point_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("grammar_points.id", ondelete="CASCADE"), nullable=False
    )
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    correct_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 首次进入错题本时间；后续答错不更新
    added_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    last_wrong_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )


__all__ = ["GrammarAnswer", "GrammarAttempt", "GrammarPointProgress", "GrammarWrongPoint"]
