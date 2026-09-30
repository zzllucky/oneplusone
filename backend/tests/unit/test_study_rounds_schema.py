"""轮次表结构：索引与约束必须存在（T028 并发安全的前置）。"""

from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.unit


def test_study_rounds_indexes_exist(db):
    names = {
        row[0]
        for row in db.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='study_rounds'")
        ).fetchall()
    }

    assert "uq_study_rounds_open" in names, "缺少单进行中轮次的部分唯一索引"
    assert "ix_study_rounds_user_completed" in names


def test_study_rounds_partial_index_sql(db):
    sql = db.execute(
        text("SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_study_rounds_open'")
    ).scalar()

    assert sql and "completed_at IS NULL" in sql, "部分索引条件丢失"
