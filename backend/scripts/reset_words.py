"""清理词表数据源，为重新导入词表做准备。

删除 ``words`` 及依赖词的业务数据（每日任务、测验记录、错题本），
**保留账号与用户设置**（users / user_settings）。

用法::

    python scripts/reset_words.py            # 使用 DB_PATH 或默认 data/app.db
    DB_PATH=/opt/1plus1/data/app.db python scripts/reset_words.py

执行前会自动备份数据库为 ``<db>.bak.<时间戳>``。
清理后需重新导入词表::

    alembic downgrade 001 && alembic upgrade head
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

# 顺序：先删依赖 words 的业务表，再删 words；users / user_settings 保留
TABLES = [
    "wrong_words",
    "quiz_answers",
    "quiz_attempts",
    "daily_set_items",
    "daily_sets",
    "words",
]


def reset(db_path: Path) -> int:
    if not db_path.exists():
        print(f"[reset] 数据库不存在: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    backup = db_path.with_name(f"{db_path.name}.bak.{time.strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(db_path, backup)
    print(f"[reset] 已备份: {backup}")

    conn.execute("PRAGMA foreign_keys=OFF")
    for table in TABLES:
        try:
            deleted = conn.execute(f"DELETE FROM {table}").rowcount
            print(f"[reset] {table}: 删除 {deleted} 行")
        except sqlite3.Error as exc:  # pragma: no cover - 表不存在时跳过
            print(f"[reset] {table}: 跳过（{exc}）")
    conn.commit()

    remaining = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    print(f"[reset] 完成：words 剩余 {remaining} 行，账号保留 {users} 个")
    return 0


def main() -> int:
    db_path = Path(os.environ.get("DB_PATH", "data/app.db"))
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    return reset(db_path)


if __name__ == "__main__":
    sys.exit(main())
