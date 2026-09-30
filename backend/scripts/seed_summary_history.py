"""本地造数：为指定账号生成最近 N 天的历史行为（仅供 quickstart 手工验证）。

只**新增**既有表的数据、不删除任何数据；同一日期重复执行会跳过（幂等）。
不进 Docker 镜像、不在生产执行；请勿对真实学习数据运行。

用法：
    cd backend && python scripts/seed_summary_history.py --user stu01 --days 30
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT / "src"))

from app import db as db_module  # noqa: E402
from app.config import settings  # noqa: E402
from app.models.base import utcnow  # noqa: E402
from app.models.daily_set import DailySet, DailySetItem  # noqa: E402
from app.models.quiz import QuizAnswer, QuizAttempt  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.word import Word  # noqa: E402

LOCAL_OFFSET_MINUTES = 8 * 60  # Asia/Shanghai


def _local_to_utc(day: dt.date, hour: int, minute: int) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(hour, minute)) - dt.timedelta(
        minutes=LOCAL_OFFSET_MINUTES
    )


def _pick_word_ids(session, count: int) -> list[int]:
    ids = [
        row[0]
        for row in session.query(Word.id).order_by(Word.id).limit(count).all()
    ]
    return ids


def seed(session, user_id: int, days: int, seed_value: int = 20260930) -> None:
    random.seed(seed_value)
    today = dt.date.today()
    word_pool = _pick_word_ids(session, 60)
    if not word_pool:
        raise SystemExit("词库为空，请先执行迁移（alembic upgrade head）")

    created = 0
    for offset in range(days - 1, -1, -1):
        day = today - dt.timedelta(days=offset)
        existing = (
            session.query(DailySet)
            .filter(DailySet.user_id == user_id, DailySet.study_date == day)
            .first()
        )
        if existing is not None:
            continue  # 幂等：该日已有数据则跳过

        kind = offset % 3
        if kind == 2:
            continue  # 完全无记录的日期（灰色）

        total = 5 if kind == 1 else random.choice([3, 12, 18, 25, 35])
        viewed = 0 if kind == 1 else total  # kind=1：只打开过（浅绿）
        daily_set = DailySet(user_id=user_id, study_date=day, created_at=utcnow())
        session.add(daily_set)
        session.flush()
        for index in range(total):
            session.add(
                DailySetItem(
                    daily_set_id=daily_set.id,
                    word_id=word_pool[index % len(word_pool)],
                    order_index=index + 1,
                    viewed_at=utcnow() if index < viewed else None,
                )
            )
        session.flush()

        if viewed > 0:
            # 今日测验：与当日集合同日
            attempt = QuizAttempt(
                user_id=user_id,
                kind="daily",
                study_date=day,
                started_at=_local_to_utc(day, 19, 0),
                finished_at=_local_to_utc(day, 19, 10),
                total_count=min(viewed, 10),
                correct_count=max(min(viewed, 10) - 2, 0),
                wrong_count=min(2, min(viewed, 10)),
            )
            session.add(attempt)
            session.flush()

            # 两类专项练习（作答时刻决定归日）
            for practice_kind, hour in (("review", 20), ("archive", 21)):
                practice = QuizAttempt(
                    user_id=user_id,
                    kind=practice_kind,
                    study_date=None,
                    started_at=_local_to_utc(day, hour, 0),
                    finished_at=_local_to_utc(day, hour, 5),
                    total_count=4,
                    correct_count=3,
                    wrong_count=1,
                )
                session.add(practice)
                session.flush()
                for index in range(4):
                    session.add(
                        QuizAnswer(
                            attempt_id=practice.id,
                            word_id=word_pool[(index + hour) % len(word_pool)],
                            question_type="en2zh",
                            choice_index=0 if index < 3 else 1,
                            is_correct=index < 3,
                            answered_at=_local_to_utc(day, hour, index + 1),
                        )
                    )
        created += 1

    session.commit()
    print(f"[seed] 用户 {user_id}：新增 {created} 天的历史记录（共 {days} 天窗口）")


def main() -> None:
    parser = argparse.ArgumentParser(description="造学习日历总结的历史数据")
    parser.add_argument("--user", required=True, help="登录名（login_name）")
    parser.add_argument("--days", type=int, default=30, help="生成最近 N 天（默认 30）")
    parser.add_argument("--db", default=settings.db_path, help="数据库文件路径")
    args = parser.parse_args()

    db_module.init_engine(args.db)
    session = db_module.SessionLocal()
    try:
        user = session.query(User).filter(User.login_name == args.user).first()
        if user is None:
            raise SystemExit(f"未找到用户：{args.user}（请先在页面上注册）")
        seed(session, user.id, args.days)
    finally:
        session.close()


if __name__ == "__main__":
    main()
