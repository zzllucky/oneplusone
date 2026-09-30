"""004 学习轮次表（词库循环学习）

- 新建 ``study_rounds``（轮序号 + 取词游标 + 覆盖/完成时间）

注意：001 迁移直接以 ``Base.metadata`` 建表，全新库执行 001 时可能已包含本表，
因此本迁移按"存在则跳过"的幂等方式编写，新旧库都能执行。

**不回填历史账号**（范围排除，见 research R-005）：不读取 ``daily_set_items``，
不为任何已有账号预建轮次行。

Revision ID: 004
Revises: 003
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "study_rounds" in _existing_tables():
        return

    op.create_table(
        "study_rounds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("cursor_word_id", sa.Integer(), nullable=False),
        sa.Column("started_on", sa.Date(), nullable=False),
        sa.Column("covered_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "round_no", name="uq_study_rounds_user_round"),
    )
    # 单账号单"进行中"轮次（注意：sqlite_where 必须是 SQL 表达式元素，不能是裸字符串）
    op.create_index(
        "uq_study_rounds_open",
        "study_rounds",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("completed_at IS NULL"),
    )
    op.create_index(
        "ix_study_rounds_user_completed", "study_rounds", ["user_id", "completed_at"]
    )


def downgrade() -> None:
    if "study_rounds" in _existing_tables():
        op.drop_table("study_rounds")
