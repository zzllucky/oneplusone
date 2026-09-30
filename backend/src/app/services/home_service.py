"""首页摘要：用户信息 + 每日目标 + 今日进度 + 错题总数 + 轮次信息。"""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import (
    round_service,
    settings_service,
    study_service,
    wrong_word_service,
)


def summary(db: Session, user: User) -> dict:
    goal = settings_service.get_daily_goal(db, user.id)
    # 首页展示今日进度，需要当日集合存在（首次访问即按目标生成）
    study_service.get_or_create_today_set(db, user.id, goal)
    today = study_service.today_summary(db, user.id, goal)
    return {
        "user": {
            "id": user.id,
            "login_name": user.login_name,
            "nickname": user.nickname,
        },
        "daily_goal": goal,
        "today": {
            "study_date": today.study_date.isoformat(),
            "total_count": today.total_count,
            "viewed_count": today.viewed_count,
            "all_viewed": today.all_viewed,
            "quiz_unlocked": today.quiz_unlocked,
        },
        "wrong_word_count": wrong_word_service.count_wrong_words(db, user.id),
        "archive_word_count": wrong_word_service.count_archive_words(db, user.id),
        # 轮次信息必须经 round_service.progress 读取：其内部先执行轮末补记，
        # 保证首页与学习页看到同一轮数（FR-014 / SC-006）
        "completed_rounds": round_service.completed_rounds(db, user.id),
        "current_round": asdict(round_service.progress(db, user.id)),
    }
