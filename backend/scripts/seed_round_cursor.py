"""本地造数脚本：把指定账号的当前轮游标推进到"只剩 N 个单词"。

仅供 quickstart 场景 A / B / D / E 与新功能手工验证使用，**不进 Docker 镜像**。

用法（在 backend/ 目录下）：

    python scripts/seed_round_cursor.py --user stu01 --remaining 20
    python scripts/seed_round_cursor.py --user-id 1 --remaining 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = BACKEND_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sqlalchemy import select  # noqa: E402

from app import db as db_module  # noqa: E402
from app.models.study_round import StudyRound  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.word import Word  # noqa: E402
from app.services import round_service  # noqa: E402


def _resolve_user_id(session, user: str | None, user_id: int | None) -> int:
    if user_id is not None:
        return user_id
    assert user is not None
    found = session.scalar(select(User).where(User.login_name == user))
    if found is None:
        raise SystemExit(f"未找到账号：{user}")
    return found.id


def main() -> int:
    parser = argparse.ArgumentParser(description="推进账号的当前轮取词游标")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user", help="登录名，如 stu01")
    group.add_argument("--user-id", type=int, help="账号 id")
    parser.add_argument("--remaining", type=int, default=20, help="本轮剩余单词数")
    parser.add_argument("--db", help="数据库路径（默认取环境变量 DB_PATH 或 data/app.db）")
    args = parser.parse_args()

    db_path = args.db or db_module.settings.db_path
    db_module.init_engine(str(db_path))
    session = db_module.SessionLocal()
    try:
        user_id = _resolve_user_id(session, args.user, args.user_id)
        word_ids = list(session.scalars(select(Word.id).order_by(Word.id)).all())
        if not word_ids:
            raise SystemExit("词库为空，请先执行 alembic upgrade head")

        remaining = max(0, min(args.remaining, len(word_ids)))
        cursor = word_ids[len(word_ids) - remaining] if remaining else word_ids[-1] + 1

        round_ = round_service.ensure_open_round(session, user_id)
        round_.cursor_word_id = cursor
        round_.covered_at = None
        session.commit()
        print(
            f"[seed] user_id={user_id} round_no={round_.round_no} "
            f"cursor_word_id={cursor} remaining={remaining} db={db_path}"
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
