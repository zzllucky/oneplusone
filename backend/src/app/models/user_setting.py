"""user_settings —— 用户配置（每日单词目标）。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class UserSetting(Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        CheckConstraint("daily_goal BETWEEN 1 AND 200", name="ck_user_settings_goal"),
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    daily_goal: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
