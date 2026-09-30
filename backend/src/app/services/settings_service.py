"""用户设置服务：每日单词目标。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError
from app.models.base import utcnow
from app.models.user_setting import UserSetting

MIN_GOAL = 1
MAX_GOAL = 200


def get_settings(db: Session, user_id: int) -> UserSetting:
    setting = db.get(UserSetting, user_id)
    if setting is None:
        setting = UserSetting(
            user_id=user_id,
            daily_goal=settings.daily_goal_default,
            updated_at=utcnow(),
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def update_settings(db: Session, user_id: int, daily_goal: int) -> UserSetting:
    if not isinstance(daily_goal, int) or not (MIN_GOAL <= daily_goal <= MAX_GOAL):
        raise AppError("goal_out_of_range", status_code=422)

    setting = get_settings(db, user_id)
    setting.daily_goal = daily_goal
    setting.updated_at = utcnow()
    db.commit()
    db.refresh(setting)

    # FR-010：当日尚未浏览任何单词 → 立即按新目标重算当日集合；已开始则保持不动
    from app.services import study_service

    study_service.reset_today_set_if_not_started(db, user_id, daily_goal)
    return setting


def get_daily_goal(db: Session, user_id: int) -> int:
    return get_settings(db, user_id).daily_goal
