"""语法知识点 / 题目 / 选项 —— 由 seeds/grammar 下的 JSON 幂等导入。

三张表的关系：

- ``grammar_points``：一个知识点 = 一张学习卡（如 ``G-A01`` 比较级构成）
- ``grammar_questions``：题目，来源分两种
  - ``source='card'`` —— 卡内学后检测（``cards/*.json`` 的 check）
  - ``source='bank'`` —— 题库练习（``questions/*.json``）
- ``grammar_options``：题目的选项，正确项唯一，错项带错因说明

卡片的教研内容（猜一猜、规则讲解、对比表）结构多变，整体以 JSON 存在
``grammar_points.payload``；题目与选项是答题与判分要用到的，拆成独立表。
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class GrammarPoint(Base):
    """语法知识点（一张学习卡）。"""

    __tablename__ = "grammar_points"
    __table_args__ = (
        CheckConstraint("depth IN ('核心','了解')", name="ck_grammar_points_depth"),
        CheckConstraint(
            "card_type IN ('rule','contrast','memorize')",
            name="ck_grammar_points_card_type",
        ),
    )

    # 形如 G-A01；合并卡以主知识点命名，覆盖的其他 id 记在 covers
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    module: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    module_name: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    depth: Mapped[str] = mapped_column(String(8), nullable=False)
    card_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # 大纲展示顺序：先按模块、再按知识点编号
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 教研内容：guess / rule 或 contrast / guess_callback
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # 覆盖的大纲知识点 id（普通卡 = [自身]，合并卡为多个）
    covers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )

    questions: Mapped[list["GrammarQuestion"]] = relationship(
        back_populates="point", cascade="all, delete-orphan"
    )


class GrammarQuestion(Base):
    """语法题（卡内检测 + 题库练习共用一张表）。"""

    __tablename__ = "grammar_questions"
    __table_args__ = (
        CheckConstraint(
            "source IN ('card','bank')", name="ck_grammar_questions_source"
        ),
        CheckConstraint("level IN ('L1','L2','L3')", name="ck_grammar_questions_level"),
    )

    # 卡内检测形如 G-A01-Q01；题库形如 G-A01-L1-01
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    point_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("grammar_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(8), nullable=False)
    level: Mapped[str] = mapped_column(String(2), nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    # 答错时回链的知识点 id（种子里等于 point_id）
    error_tag: Mapped[str | None] = mapped_column(String(16), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )

    point: Mapped[GrammarPoint] = relationship(back_populates="questions")
    options: Mapped[list["GrammarOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class GrammarOption(Base):
    """题目选项：正确项唯一，错项的 feedback 说明错在哪里。"""

    __tablename__ = "grammar_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("grammar_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # A / B / C / D
    key: Mapped[str] = mapped_column(String(2), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    question: Mapped[GrammarQuestion] = relationship(back_populates="options")


__all__ = ["GrammarOption", "GrammarPoint", "GrammarQuestion"]
