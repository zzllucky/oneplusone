"""账号接口：注册 / 登录 / 当前用户。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.security import create_access_token
from app.services import auth_service, settings_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut(id=user.id, login_name=user.login_name, nickname=user.nickname),
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.register(
        db,
        login_name=payload.login_name,
        nickname=payload.nickname,
        password=payload.password,
    )
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.authenticate(
        db, login_name=payload.login_name, password=payload.password
    )
    return _token_response(user)


@router.get("/me", response_model=MeResponse)
def me(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MeResponse:
    return MeResponse(
        id=user.id,
        login_name=user.login_name,
        nickname=user.nickname,
        daily_goal=settings_service.get_daily_goal(db, user.id),
    )
