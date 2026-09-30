"""模型公共基类与混入。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> dt.datetime:
    """统一取 UTC 时间（naive），全库一致。"""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, server_default=func.now()
    )


__all__ = ["Base", "TimestampMixin", "utcnow"]
