"""用户设置接口：每日单词目标。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.settings import SettingsOut, SettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SettingsOut:
    setting = settings_service.get_settings(db, user.id)
    return SettingsOut(daily_goal=setting.daily_goal, updated_at=setting.updated_at)


@router.put("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingsOut:
    setting = settings_service.update_settings(db, user.id, payload.daily_goal)
    return SettingsOut(daily_goal=setting.daily_goal, updated_at=setting.updated_at)
