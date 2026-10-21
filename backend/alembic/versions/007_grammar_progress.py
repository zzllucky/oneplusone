"""007 语法学习记录层

- 新建 ``grammar_point_progress`` / ``grammar_attempts`` / ``grammar_answers``
  / ``grammar_wrong_points`` 四张表（内容与约束见 specs/006-grammar-study/data-model.md）

注意：001 迁移直接以 ``Base.metadata`` 建表，全新库执行 001 时可能已包含本批表，
因此建表按"存在则跳过"的幂等方式编写（与 003 / 004 / 006 一致）。

**不改动任何既有表**（FR-020：语法与单词两条链路互不影响）。

Revision ID: 007
Revises: 006
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _existing_tables()

    if "grammar_point_progress" not in tables:
        op.create_table(
            "grammar_point_progress",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("point_id", sa.String(16), nullable=False),
            sa.Column("status", sa.String(12), nullable=False, server_default="not_started"),
            sa.Column("check_total", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("check_correct", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("studied_at", sa.DateTime(), nullable=True),
            sa.Column("mastered_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["point_id"], ["grammar_points.id"], ondelete="CASCADE"
            ),
            sa.CheckConstraint(
                "status IN ('not_started','learning','mastered')",
                name="ck_grammar_point_progress_status",
            ),
            sa.UniqueConstraint("user_id", "point_id", name="uq_grammar_point_progress"),
        )
        op.create_index(
            "ix_grammar_point_progress_user_status",
            "grammar_point_progress",
            ["user_id", "status"],
        )

    if "grammar_attempts" not in tables:
        op.create_table(
            "grammar_attempts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("point_id", sa.String(16), nullable=False),
            sa.Column("source", sa.String(8), nullable=False),
            sa.Column("level", sa.String(2), nullable=True),
            sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("wrong_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["point_id"], ["grammar_points.id"], ondelete="CASCADE"
            ),
            sa.CheckConstraint(
                "source IN ('card','bank')", name="ck_grammar_attempts_source"
            ),
            sa.CheckConstraint(
                "level IS NULL OR level IN ('L1','L2','L3')",
                name="ck_grammar_attempts_level",
            ),
        )
        op.create_index(
            "ix_grammar_attempts_user_point", "grammar_attempts", ["user_id", "point_id"]
        )
        op.create_index(
            "ix_grammar_attempts_user_started",
            "grammar_attempts",
            ["user_id", "started_at"],
        )

    if "grammar_answers" not in tables:
        op.create_table(
            "grammar_answers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("attempt_id", sa.Integer(), nullable=False),
            sa.Column("question_id", sa.String(32), nullable=False),
            sa.Column("choice_key", sa.String(2), nullable=False),
            sa.Column("is_correct", sa.Boolean(), nullable=False),
            sa.Column("answered_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["attempt_id"], ["grammar_attempts.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["question_id"], ["grammar_questions.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint("attempt_id", "question_id", name="uq_grammar_answer"),
        )
        op.create_index("ix_grammar_answers_question_id", "grammar_answers", ["question_id"])

    if "grammar_wrong_points" not in tables:
        op.create_table(
            "grammar_wrong_points",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("point_id", sa.String(16), nullable=False),
            sa.Column("wrong_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("correct_streak", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("added_at", sa.DateTime(), nullable=False),
            sa.Column("last_wrong_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["point_id"], ["grammar_points.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint("user_id", "point_id", name="uq_grammar_wrong_point"),
        )
        op.create_index(
            "ix_grammar_wrong_points_user_added",
            "grammar_wrong_points",
            ["user_id", "added_at"],
        )


def downgrade() -> None:
    tables = _existing_tables()
    for name in (
        "grammar_wrong_points",
        "grammar_answers",
        "grammar_attempts",
        "grammar_point_progress",
    ):
        if name in tables:
            op.drop_table(name)
