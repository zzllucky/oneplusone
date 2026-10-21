"""语法种子入库的集成测试。

依赖 ``engine`` fixture（真实 SQLite 文件 + alembic upgrade head），
校验 006 迁移建表与导入的结果，以及重复导入的幂等性。
"""

from __future__ import annotations

import pytest
from sqlalchemy import Integer, cast, func, select

from app.models.grammar import GrammarOption, GrammarPoint, GrammarQuestion
from app.seed_grammar import (
    SOURCE_BANK,
    SOURCE_CARD,
    default_seed_dir,
    import_grammar,
    load_seed_grammar,
)

pytestmark = pytest.mark.integration

# 大纲规模（syllabus.md）：21 模块 / 85 知识点
EXPECTED_POINTS = 82  # 卡片数（G-T04 并入 G-T19，G-T10/G-T11 并入 G-T09）
EXPECTED_COVERED_POINTS = 85  # covers 展开去重后的大纲知识点数


def test_points_seeded(db):
    assert db.scalar(select(func.count()).select_from(GrammarPoint)) == EXPECTED_POINTS


def test_covers_cover_all_syllabus_points(db):
    """合并卡通过 covers 覆盖大纲知识点，展开后应等于 85。"""
    covered: set[str] = set()
    for covers in db.scalars(select(GrammarPoint.covers)):
        covered.update(covers)
    assert len(covered) == EXPECTED_COVERED_POINTS


def test_merged_card_keeps_covers(db):
    point = db.get(GrammarPoint, "G-T09")
    assert point is not None
    assert point.covers == ["G-T09", "G-T10", "G-T11"]


def test_questions_seeded_from_both_sources(db):
    counts = dict(
        db.execute(
            select(GrammarQuestion.source, func.count()).group_by(
                GrammarQuestion.source
            )
        ).all()
    )
    # 卡内检测：每张卡 3 道（速记卡 G-T07 无检测题）
    assert counts.get(SOURCE_CARD) == 243
    # 题库：每个大纲知识点 6 道（L1/L2/L3 各 2），速记卡 G-T07 不出题
    # 84 × 6 = 504；合并卡 G-T09（18 题）/ G-T19（12 题）按覆盖的知识点加倍
    assert counts.get(SOURCE_BANK) == 504


def test_every_question_has_exactly_one_correct_option(db):
    rows = db.execute(
        select(GrammarQuestion.id, func.sum(cast(GrammarOption.is_correct, Integer)))
        .join(GrammarOption, GrammarOption.question_id == GrammarQuestion.id)
        .group_by(GrammarQuestion.id)
    ).all()
    assert rows, "题目应当都有选项"
    wrong = [question_id for question_id, correct in rows if correct != 1]
    assert wrong == [], f"正确项数量异常的题目: {wrong[:5]}"


def test_options_count(db):
    """每题 4 个选项：(243 卡内 + 504 题库) × 4。"""
    assert db.scalar(select(func.count()).select_from(GrammarOption)) == 2988


def test_levels_are_l1_l2_l3(db):
    levels = {
        row[0]
        for row in db.execute(
            select(GrammarQuestion.level).group_by(GrammarQuestion.level)
        ).all()
    }
    assert levels <= {"L1", "L2", "L3"}
    assert levels == {"L1", "L2", "L3"}


def test_point_order_index_is_dense(db):
    """order_index 从 0 连续递增，用于大纲顺序展示。"""
    indexes = db.scalars(select(GrammarPoint.order_index).order_by(GrammarPoint.order_index)).all()
    assert indexes == list(range(len(indexes)))


def test_module_order_follows_syllabus(db):
    """模块按大纲顺序排列：时态(T) → 语态(V) → … → 定语从句(C)。"""
    modules = db.scalars(
        select(GrammarPoint.module)
        .group_by(GrammarPoint.module)
        .order_by(func.min(GrammarPoint.order_index))
    ).all()
    assert list(modules) == ["T", "V", "F", "N", "R", "U", "B", "A", "D", "O", "S", "C"]


def test_payload_keeps_teaching_content(db):
    point = db.get(GrammarPoint, "G-A01")
    assert point is not None
    assert "guess" in point.payload
    assert "rule" in point.payload
    assert point.depth in {"核心", "了解"}


def test_questions_link_to_existing_point(db):
    orphan = db.execute(
        select(func.count())
        .select_from(GrammarQuestion)
        .where(~GrammarQuestion.point_id.in_(select(GrammarPoint.id)))
    ).scalar()
    assert orphan == 0


def test_reimport_is_idempotent(db):
    """重复导入不新增行、不重复选项。"""
    points, questions, problems = load_seed_grammar(default_seed_dir())
    assert problems == []

    before_points = db.scalar(select(func.count()).select_from(GrammarPoint))
    before_questions = db.scalar(select(func.count()).select_from(GrammarQuestion))
    before_options = db.scalar(select(func.count()).select_from(GrammarOption))

    # 结束当前读事务，确保后续查询能看到另一个连接提交的写入
    db.commit()
    added_points, added_questions, written_options = import_grammar(
        db.get_bind(), points, questions
    )
    db.expire_all()

    assert (added_points, added_questions) == (0, 0)
    assert written_options == before_options
    assert db.scalar(select(func.count()).select_from(GrammarPoint)) == before_points
    assert db.scalar(select(func.count()).select_from(GrammarQuestion)) == before_questions
    assert db.scalar(select(func.count()).select_from(GrammarOption)) == before_options
