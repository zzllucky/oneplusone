"""daily_sets / daily_set_items —— 每日学习任务与浏览状态。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class DailySet(Base):
    __tablename__ = "daily_sets"
    __table_args__ = (UniqueConstraint("user_id", "study_date", name="uq_daily_set"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # 服务端按 Asia/Shanghai 计算的日期
    study_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )

    items: Mapped[list["DailySetItem"]] = relationship(
        back_populates="daily_set", cascade="all, delete-orphan"
    )


class DailySetItem(Base):
    __tablename__ = "daily_set_items"
    __table_args__ = (
        UniqueConstraint("daily_set_id", "word_id", name="uq_daily_set_word"),
        Index("ix_daily_set_items_order", "daily_set_id", "order_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    daily_set_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("daily_sets.id", ondelete="CASCADE"), nullable=False
    )
    word_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("words.id"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # NULL = 未浏览；标记浏览幂等，保留首次时间
    viewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    daily_set: Mapped[DailySet] = relationship(back_populates="items")
