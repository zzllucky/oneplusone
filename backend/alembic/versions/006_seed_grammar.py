"""006 语法知识点、题目与选项

- 新建 ``grammar_points`` / ``grammar_questions`` / ``grammar_options`` 三张表
- 从 ``seeds/grammar`` 导入 82 个知识点、729 道题目（卡内检测 + 题库）

注意：001 迁移直接以 ``Base.metadata`` 建表，全新库执行 001 时可能已包含本表，
因此建表按"存在则跳过"的幂等方式编写（与 003 / 004 一致）；
**数据导入不受影响**，每次都按主键 upsert，重复执行结果不变。

Revision ID: 006
Revises: 005
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.seed_grammar import default_seed_dir, import_grammar, load_seed_grammar

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    tables = _existing_tables()

    if "grammar_points" not in tables:
        op.create_table(
            "grammar_points",
            sa.Column("id", sa.String(16), primary_key=True),
            sa.Column("module", sa.String(2), nullable=False),
            sa.Column("module_name", sa.String(32), nullable=False),
            sa.Column("title", sa.String(64), nullable=False),
            sa.Column("depth", sa.String(8), nullable=False),
            sa.Column("card_type", sa.String(16), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("covers", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("depth IN ('核心','了解')", name="ck_grammar_points_depth"),
            sa.CheckConstraint(
                "card_type IN ('rule','contrast','memorize')",
                name="ck_grammar_points_card_type",
            ),
        )
        op.create_index("ix_grammar_points_module", "grammar_points", ["module"])

    if "grammar_questions" not in tables:
        op.create_table(
            "grammar_questions",
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("point_id", sa.String(16), nullable=False),
            sa.Column("source", sa.String(8), nullable=False),
            sa.Column("level", sa.String(2), nullable=False),
            sa.Column("stem", sa.Text(), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=False),
            sa.Column("error_tag", sa.String(16), nullable=True),
            sa.Column("order_index", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["point_id"], ["grammar_points.id"], ondelete="CASCADE"
            ),
            sa.CheckConstraint(
                "source IN ('card','bank')", name="ck_grammar_questions_source"
            ),
            sa.CheckConstraint(
                "level IN ('L1','L2','L3')", name="ck_grammar_questions_level"
            ),
        )
        op.create_index(
            "ix_grammar_questions_point_id", "grammar_questions", ["point_id"]
        )

    if "grammar_options" not in tables:
        op.create_table(
            "grammar_options",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("question_id", sa.String(32), nullable=False),
            sa.Column("key", sa.String(2), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("is_correct", sa.Boolean(), nullable=False),
            sa.Column("feedback", sa.Text(), nullable=True),
            sa.Column("order_index", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["question_id"], ["grammar_questions.id"], ondelete="CASCADE"
            ),
        )
        op.create_index(
            "ix_grammar_options_question_id", "grammar_options", ["question_id"]
        )

    points, questions, problems = load_seed_grammar(default_seed_dir())
    if not points:
        return

    added_points, added_questions, written_options = import_grammar(
        bind, points, questions
    )
    print(
        f"[006] 语法种子导入完成：知识点新增 {added_points} 条，"
        f"题目新增 {added_questions} 条，选项写入 {written_options} 条"
        + (f"（校验问题 {len(problems)} 条）" if problems else "")
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _existing_tables()
    for table in ("grammar_options", "grammar_questions", "grammar_points"):
        if table in tables:
            op.drop_table(table)
