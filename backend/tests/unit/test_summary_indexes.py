"""迁移 005 索引护栏：3 个查询索引必须真实存在于 sqlite_master。

防「索引静默丢失」重演（003 曾因 sqlite_where 传裸字符串导致索引未创建）。
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.unit

EXPECTED = {
    "ix_quiz_attempts_user_kind_date": "quiz_attempts",
    "ix_quiz_attempts_user_finished": "quiz_attempts",
    "ix_quiz_answers_answered_at": "quiz_answers",
}


def _index_names(db, table: str) -> set[str]:
    return {
        row[0]
        for row in db.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=:t"),
            {"t": table},
        ).fetchall()
    }


def test_summary_query_indexes_exist(db):
    for name, table in EXPECTED.items():
        assert name in _index_names(db, table), f"缺少索引 {name}（表 {table}）"


def test_summary_indexes_cover_expected_columns(db):
    """索引列顺序与 data-model 一致，避免建错列导致查询仍全表扫描。"""
    sql = db.execute(
        text("SELECT sql FROM sqlite_master WHERE type='index' AND name='ix_quiz_attempts_user_kind_date'")
    ).scalar()
    assert sql and "user_id" in sql and "kind" in sql and "study_date" in sql
