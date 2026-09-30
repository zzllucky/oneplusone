"""口令哈希与 JWT 签发 / 校验。

安全约束：明文口令与哈希只在本模块内流转，绝不写入日志或响应。
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: int) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + dt.timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> int | None:
    """解析 token，成功返回 user_id；任何失败返回 None。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    try:
        return int(subject)
    except (TypeError, ValueError):
        return None
