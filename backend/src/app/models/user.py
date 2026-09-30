"""users —— 注册用户（学生）。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 登录名原文：3–20 位字母 / 数字 / 下划线
    login_name: Mapped[str] = mapped_column(String(32), nullable=False)
    # 小写归一值：注册去重与登录匹配一律使用它
    login_name_norm: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )
    # 昵称仅展示，允许重复
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    # bcrypt 哈希，永不返回给客户端
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
