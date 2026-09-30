"""学习服务：当日集合生成（UTC+8）、浏览标记、进度与解锁判定。"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError
from app.models.base import utcnow
from app.models.daily_set import DailySet, DailySetItem
from app.models.word import Word


def today_date(now: dt.datetime | None = None) -> dt.date:
    """按服务端统一时区（默认 Asia/Shanghai）计算"当日"。"""
    moment = now or dt.datetime.now(dt.timezone.utc)
    return moment.astimezone(ZoneInfo(settings.timezone)).date()


@dataclass
class TodaySummary:
    study_date: dt.date
    total_count: int
    viewed_count: int
    all_viewed: bool
    quiz_unlocked: bool
    library_exhausted: bool


def get_today_set(db: Session, user_id: int) -> DailySet | None:
    return db.scalar(
        select(DailySet).where(
            DailySet.user_id == user_id, DailySet.study_date == today_date()
        )
    )


def learned_word_ids(db: Session, user_id: int) -> set[int]:
    """历史累计学过的单词（曾出现在任意每日集合中）。

    注意：自 003（词库循环学习）起，**取词不再依赖本函数**（改为按当前轮游标取词，
    支持多轮学习）；保留仅供统计与其它只读场景使用。
    """
    rows = db.execute(
        select(DailySetItem.word_id)
        .join(DailySet, DailySet.id == DailySetItem.daily_set_id)
        .where(DailySet.user_id == user_id)
    ).all()
    return {row[0] for row in rows}


def get_or_create_today_set(db: Session, user_id: int, daily_goal: int) -> DailySet:
    """首次访问按每日目标生成本轮当日集合（词库原顺序）；当日重复访问返回同一集合。

    取词范围由 ``round_service`` 的当前轮游标决定（FR-001 / FR-002 / FR-012）：
    词库被学完后自动进入下一轮，不再出现"无词可分配"。
    """
    from app.services import round_service

    existing = get_today_set(db, user_id)
    if existing is not None:
        return existing

    word_ids = round_service.allocate_word_ids(db, user_id, daily_goal)
    words = (
        list(db.scalars(select(Word).where(Word.id.in_(word_ids)).order_by(Word.id)).all())
        if word_ids
        else []
    )

    daily_set = DailySet(
        user_id=user_id, study_date=today_date(), created_at=utcnow()
    )
    db.add(daily_set)
    db.flush()

    for index, word in enumerate(words, start=1):
        db.add(
            DailySetItem(
                daily_set_id=daily_set.id,
                word_id=word.id,
                order_index=index,
                viewed_at=None,
            )
        )
    db.commit()
    if word_ids:
        round_service.advance_cursor(db, user_id, word_ids)
    db.refresh(daily_set)
    return daily_set


def reset_today_set_if_not_started(db: Session, user_id: int, daily_goal: int) -> bool:
    """当日**尚未浏览任何单词**时按新目标重算当日集合；已浏览则保持不动。

    对应 FR-010：目标变更在"未开始"时立即生效，已开始则次日生效。
    返回是否发生重算（供调用方提示）。

    003 注：本规则在**每一轮**中与首轮一致（US3）。重算时会把撤销的单词
    还给当前轮游标（``round_service.rewind_cursor``），保证本轮不漏词。
    """
    daily_set = get_today_set(db, user_id)
    if daily_set is None:
        return False
    if any(item.viewed_at is not None for item in daily_set.items):
        return False

    from app.services import round_service

    # 撤销的这批单词要还给当前轮游标，重算时才能重新参与分配
    removed_ids = [item.word_id for item in daily_set.items]
    db.delete(daily_set)  # items 由 relationship cascade 一并删除
    db.commit()
    round_service.rewind_cursor(db, user_id, removed_ids)
    get_or_create_today_set(db, user_id, daily_goal)
    return True


def today_items(db: Session, user_id: int) -> list[DailySetItem]:
    daily_set = get_today_set(db, user_id)
    if daily_set is None:
        return []
    return sorted(daily_set.items, key=lambda item: item.order_index)


def today_summary(db: Session, user_id: int, daily_goal: int) -> TodaySummary:
    items = today_items(db, user_id)
    total = len(items)
    viewed = sum(1 for item in items if item.viewed_at is not None)
    library_exhausted = False
    if total == 0:
        # 当日集合尚未生成：按"本轮剩余是否不足每日目标"判断（循环学习下不存在无词可学）
        from app.services import round_service

        library_exhausted = round_service.remaining_in_round(db, user_id) < daily_goal
    else:
        library_exhausted = total < daily_goal

    return TodaySummary(
        study_date=today_date(),
        total_count=total,
        viewed_count=viewed,
        all_viewed=total > 0 and viewed == total,
        quiz_unlocked=total > 0 and viewed == total,
        library_exhausted=library_exhausted,
    )


def mark_viewed(db: Session, user_id: int, word_id: int) -> tuple[bool, TodaySummary, int]:
    """标记浏览（幂等）：仅当日集合内的单词可标记，保留首次 viewed_at。"""
    daily_set = get_today_set(db, user_id)
    if daily_set is None:
        raise AppError("word_not_in_today_set", status_code=404)

    item = db.scalar(
        select(DailySetItem).where(
            DailySetItem.daily_set_id == daily_set.id,
            DailySetItem.word_id == word_id,
        )
    )
    if item is None:
        raise AppError("word_not_in_today_set", status_code=404)

    newly_viewed = item.viewed_at is None
    if newly_viewed:
        item.viewed_at = utcnow()
        db.commit()

    from app.services.settings_service import get_daily_goal

    return newly_viewed, today_summary(db, user_id, get_daily_goal(db, user_id)), daily_set.id
