"""003 错题熟练度与永久错题库

- ``wrong_words`` 增加 ``wrong_count`` / ``correct_streak`` / ``last_wrong_at``
- 新建 ``wrong_word_archive``（永久错题库：只累计次数、无时间、永不移除）
- ``quiz_attempts.kind`` 允许 ``'archive'``（错题库专项练习）

注意：001 迁移直接以 ``Base.metadata`` 建表，全新库执行 001 时已经包含本迁移的
表与列。因此本迁移全部按"存在则跳过"的幂等方式编写，新旧库都能执行。

Revision ID: 003
Revises: 002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _existing_columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in _existing_tables():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _attempt_kind_allows_archive() -> bool:
    sql = op.get_bind().exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='quiz_attempts'"
    ).scalar()
    return bool(sql) and "'archive'" in sql


def upgrade() -> None:
    tables = _existing_tables()

    if "wrong_words" in tables:
        columns = _existing_columns("wrong_words")
        if "wrong_count" not in columns:
            op.add_column(
                "wrong_words",
                sa.Column("wrong_count", sa.Integer(), nullable=False, server_default="1"),
            )
        if "correct_streak" not in columns:
            op.add_column(
                "wrong_words",
                sa.Column(
                    "correct_streak", sa.Integer(), nullable=False, server_default="0"
                ),
            )
        if "last_wrong_at" not in columns:
            op.add_column(
                "wrong_words", sa.Column("last_wrong_at", sa.DateTime(), nullable=True)
            )

    if "wrong_word_archive" not in tables:
        op.create_table(
            "wrong_word_archive",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("word_id", sa.Integer(), nullable=False),
            sa.Column("wrong_count", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "word_id", name="uq_wrong_word_archive"),
        )
        op.create_index(
            "ix_wrong_word_archive_user", "wrong_word_archive", ["user_id", "id"]
        )

    if "quiz_attempts" in tables and not _attempt_kind_allows_archive():
        with op.batch_alter_table("quiz_attempts") as batch_op:
            batch_op.drop_constraint("ck_quiz_attempts_kind", type_="check")
            batch_op.create_check_constraint(
                "ck_quiz_attempts_kind", "kind IN ('daily','review','archive')"
            )


def downgrade() -> None:
    tables = _existing_tables()

    if "quiz_attempts" in tables and _attempt_kind_allows_archive():
        with op.batch_alter_table("quiz_attempts") as batch_op:
            batch_op.drop_constraint("ck_quiz_attempts_kind", type_="check")
            batch_op.create_check_constraint(
                "ck_quiz_attempts_kind", "kind IN ('daily','review')"
            )

    if "wrong_word_archive" in tables:
        op.drop_table("wrong_word_archive")

    if "wrong_words" in tables:
        columns = _existing_columns("wrong_words")
        for column in ("last_wrong_at", "correct_streak", "wrong_count"):
            if column in columns:
                op.drop_column("wrong_words", column)
