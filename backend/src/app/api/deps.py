"""依赖注入：数据库会话与当前登录用户。"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models.user import User
from app.security import decode_access_token
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """解析 Bearer token；缺失或失效一律 401 `unauthorized`。"""
    if credentials is None or not credentials.credentials:
        raise AppError("unauthorized", status_code=401)

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise AppError("unauthorized", status_code=401)

    user = auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise AppError("unauthorized", status_code=401)
    return user
