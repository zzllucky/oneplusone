"""words —— 内置词库（由 seeds/words.txt 统一格式幂等导入）。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class Word(Base, TimestampMixin):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spelling: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    meaning_zh: Mapped[str] = mapped_column(String(255), nullable=False)
    phrase: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phonetic: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
