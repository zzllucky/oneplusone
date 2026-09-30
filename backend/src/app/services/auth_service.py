"""账号服务：注册、登录校验、按 id 取用户。"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError
from app.models.user import User
from app.models.user_setting import UserSetting
from app.models.base import utcnow
from app.security import hash_password, verify_password

LOGIN_NAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")

MIN_PASSWORD_LENGTH = 6
MAX_NICKNAME_LENGTH = 24


def _validate_login_name(login_name: str) -> str:
    value = (login_name or "").strip()
    if not LOGIN_NAME_RE.fullmatch(value):
        raise AppError("invalid_login_name", status_code=422)
    return value


def _validate_nickname(nickname: str) -> str:
    value = (nickname or "").strip()
    if not value or len(value) > MAX_NICKNAME_LENGTH:
        raise AppError("invalid_nickname", status_code=422)
    return value


def _validate_password(password: str) -> str:
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise AppError("weak_password", status_code=422)
    return password


def register(
    db: Session, *, login_name: str, nickname: str, password: str
) -> User:
    """注册：校验格式 → 归一去重 → bcrypt 哈希 → 同时创建默认设置行。"""
    name = _validate_login_name(login_name)
    nick = _validate_nickname(nickname)
    raw_password = _validate_password(password)

    norm = name.lower()
    if db.scalar(select(User).where(User.login_name_norm == norm)) is not None:
        raise AppError("login_name_taken", status_code=409)

    user = User(
        login_name=name,
        login_name_norm=norm,
        nickname=nick,
        password_hash=hash_password(raw_password),
        created_at=utcnow(),
    )
    db.add(user)
    db.flush()

    db.add(
        UserSetting(
            user_id=user.id,
            daily_goal=settings.daily_goal_default,
            updated_at=utcnow(),
        )
    )
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, login_name: str, password: str) -> User:
    """登录：按小写归一匹配；失败一律 invalid_credentials（不区分原因）。"""
    name = (login_name or "").strip()
    user = db.scalar(select(User).where(User.login_name_norm == name.lower()))
    if user is None or not verify_password(password or "", user.password_hash):
        raise AppError("invalid_credentials", status_code=401)
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)
