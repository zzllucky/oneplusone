"""002 导入内置词表种子

从 ``seeds/words.txt`` 读取统一格式词表（``单词 词性.释义 | 短语1；短语2``），
按 ``spelling`` **幂等 upsert** 到 ``words`` 表：
- 已存在（按 spelling 判断）→ 更新 meaning_zh / phrase / phonetic
- 不存在 → 插入

重复执行结果不变；不删除任何用户数据（R-001 / R-009）。

Revision ID: 002
Revises: 001
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

from app.seed_words import load_seed_words

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "seeds", "words.txt")


def upgrade() -> None:
    rows = load_seed_words(os.path.abspath(SEED_PATH))
    if not rows:
        return

    bind = op.get_bind()
    words = sa.table(
        "words",
        sa.column("spelling", sa.String),
        sa.column("meaning_zh", sa.String),
        sa.column("phrase", sa.String),
        sa.column("phonetic", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    existing = {
        row[0]: row[1]
        for row in bind.execute(sa.select(words.c.spelling, words.c.meaning_zh))
    }

    to_insert = []
    updated = 0
    for word in rows:
        payload = {
            "spelling": word.spelling,
            "meaning_zh": word.meaning_zh,
            "phrase": word.phrase,
            "phonetic": word.phonetic,
            "created_at": now,
        }
        if payload["spelling"] in existing:
            bind.execute(
                words.update()
                .where(words.c.spelling == payload["spelling"])
                .values(
                    meaning_zh=payload["meaning_zh"],
                    phrase=payload["phrase"],
                    phonetic=payload["phonetic"],
                )
            )
            updated += 1
        else:
            to_insert.append(payload)

    if to_insert:
        bind.execute(words.insert(), to_insert)

    print(f"[002] 词表导入完成：新增 {len(to_insert)} 条，更新 {updated} 条")


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM words"))
