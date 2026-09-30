"""005 汇总查询索引（学习日历总结）

仅创建 3 个**查询索引**，不建表、不改字段、不回填数据：

- ``ix_quiz_attempts_user_kind_date``：按月查今日测验（``kind='daily'`` + ``study_date``）
- ``ix_quiz_attempts_user_finished``：按完成时间筛选已完成轮次
- ``ix_quiz_answers_answered_at``：专项练习按作答时刻归日的范围扫描

幂等：索引已存在则跳过（全新库由 001 建表时可能已带上同名索引）。

**不使用** ``sqlite_where``（003 曾因传裸字符串导致 ``AttributeError`` 且索引静默丢失）。

Revision ID: 005
Revises: 004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_quiz_attempts_user_kind_date", "quiz_attempts", ["user_id", "kind", "study_date"]),
    ("ix_quiz_attempts_user_finished", "quiz_attempts", ["user_id", "finished_at"]),
    ("ix_quiz_answers_answered_at", "quiz_answers", ["answered_at"]),
]


def _existing_indexes() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    names: set[str] = set()
    for table in ("quiz_attempts", "quiz_answers"):
        if table not in tables:
            continue
        names |= {index["name"] for index in inspector.get_indexes(table)}
    return names


def upgrade() -> None:
    existing = _existing_indexes()
    for name, table, columns in INDEXES:
        if name in existing:
            continue
        op.create_index(name, table, columns)


def downgrade() -> None:
    existing = _existing_indexes()
    for name, table, _columns in INDEXES:
        if name in existing:
            op.drop_index(name, table_name=table)
