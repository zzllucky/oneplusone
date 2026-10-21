"""语法种子解析器的单元测试。

覆盖：
- 卡片（rule / contrast 两种）解析为知识点 + 卡内检测题
- 题库文件解析为练习题
- 选项答案标记（``answer: true`` / ``distractor``）的归一
- 不变量校验（每题恰好一个正确项、题库 point_id 必须有对应卡）
- 目录级加载与排序
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import seed_grammar
from app.seed_grammar import (
    SOURCE_BANK,
    SOURCE_CARD,
    SeedOption,
    SeedPoint,
    default_seed_dir,
    load_seed_grammar,
    parse_card,
    parse_question_bank,
    validate_seed,
)

pytestmark = pytest.mark.unit


def _rule_card() -> dict:
    return {
        "id": "G-A01",
        "type": "rule",
        "module": "A",
        "module_name": "形容词",
        "title": "比较级构成",
        "depth": "核心",
        "guess": {
            "examples": [{"en": "Tom is taller than Jim.", "zh": "汤姆比吉姆高。"}],
            "question": "多音节词怎么变比较级？",
            "options": [
                {"key": "A", "text": "前面加 more", "feedback": "对！"},
                {"key": "B", "text": "后面加 -er", "feedback": "不对。"},
            ],
            "answer": "A",
        },
        "rule": {
            "rule": "多音节词前加 more / most",
            "signals": ["more", "most"],
            "anchors": [],
            "trap": {"wrong": "interestinger", "right": "more interesting", "why": "不能加 -er"},
        },
        "guess_callback": "短词加 -er，长词加 more。",
        "check": [
            {
                "id": "G-A01-Q01",
                "level": "L1",
                "type": "choice",
                "stem": "Which is ____, the sun or the moon?",
                "options": [
                    {"key": "A", "text": "big"},
                    {"key": "B", "text": "bigger", "answer": True},
                ],
                "explanation": "两者比较 → bigger。",
                "error_tag": "G-A01",
            }
        ],
    }


def _contrast_card() -> dict:
    return {
        "id": "G-R03",
        "type": "contrast",
        "module": "R",
        "module_name": "代词",
        "title": "it / one / that 替代",
        "depth": "核心",
        "contrast": {
            "left": {"label": "it", "formula": "同名同物", "anchor": "", "focus": ""},
            "right": {"label": "one", "formula": "同类异物", "anchor": "", "focus": ""},
            "diff": "",
            "traps": [],
        },
        "guess_callback": "it 是同一个，one 是同类的另一个。",
        "check": [],
    }


def _question_bank() -> dict:
    return {
        "point_id": "G-A01",
        "title": "比较级构成",
        "questions": [
            {
                "id": "G-A01-L1-01",
                "level": "L1",
                "stem": "My bag is ____ than yours.",
                "options": [
                    {"key": "A", "text": "heavy", "distractor": "有 than 要用比较级"},
                    {"key": "B", "text": "heavier", "answer": True},
                ],
                "explanation": "heavy → heavier。",
                "error_tag": "G-A01",
            },
            {
                "id": "G-A01-L2-01",
                "level": "L2",
                "stem": "This is ____ book in our library.",
                "options": [
                    {"key": "A", "text": "the most popular", "answer": True},
                    {"key": "B", "text": "the popularest", "distractor": "多音节用 most"},
                ],
                "explanation": "多音节最高级。",
                "error_tag": "G-A01",
            },
        ],
    }


# --- 卡片解析 ---


def test_parse_rule_card_fields():
    point = parse_card(_rule_card())
    assert point.id == "G-A01"
    assert point.module == "A"
    assert point.module_name == "形容词"
    assert point.title == "比较级构成"
    assert point.depth == "核心"
    assert point.card_type == "rule"
    assert point.covers == ["G-A01"]


def test_parse_rule_card_payload_excludes_check():
    """check 已拆到题目表，payload 只留教学内容。"""
    point = parse_card(_rule_card())
    assert set(point.payload) == {"guess", "rule", "guess_callback"}
    assert point.payload["guess_callback"] == "短词加 -er，长词加 more。"
    assert "check" not in point.payload


def test_parse_card_check_becomes_questions():
    point = parse_card(_rule_card())
    assert len(point.questions) == 1
    question = point.questions[0]
    assert question.id == "G-A01-Q01"
    assert question.point_id == "G-A01"
    assert question.source == SOURCE_CARD
    assert question.level == "L1"
    assert question.error_tag == "G-A01"


def test_parse_contrast_card():
    point = parse_card(_contrast_card())
    assert point.card_type == "contrast"
    assert "contrast" in point.payload
    assert point.questions == []


def test_parse_card_covers_field():
    """合并卡的 covers 覆盖多个大纲知识点。"""
    raw = _rule_card()
    raw["covers"] = ["G-T09", "G-T10", "G-T11"]
    assert parse_card(raw).covers == ["G-T09", "G-T10", "G-T11"]


# --- 选项答案归一 ---


def test_option_answer_true_marks_correct():
    question = parse_card(_rule_card()).questions[0]
    assert question.options == [
        SeedOption(key="A", text="big", is_correct=False, feedback=None),
        SeedOption(key="B", text="bigger", is_correct=True, feedback=None),
    ]


def test_option_distractor_text_becomes_feedback():
    """题库里干扰项用 distractor 字段说明错因，落到 feedback。"""
    questions = parse_question_bank(_question_bank())
    first = questions[0].options[0]
    assert first.is_correct is False
    assert first.feedback == "有 than 要用比较级"


# --- 题库解析 ---


def test_parse_question_bank_source_and_level():
    questions = parse_question_bank(_question_bank())
    assert [question.id for question in questions] == ["G-A01-L1-01", "G-A01-L2-01"]
    assert all(question.source == SOURCE_BANK for question in questions)
    assert [question.level for question in questions] == ["L1", "L2"]
    assert [question.order_index for question in questions] == [0, 1]


def test_parse_question_bank_uses_point_id():
    questions = parse_question_bank(_question_bank())
    assert all(question.point_id == "G-A01" for question in questions)


# --- 不变量校验 ---


def test_validate_accepts_valid_seed():
    points = [parse_card(_rule_card())]
    questions = parse_question_bank(_question_bank())
    assert validate_seed(points, questions) == []


def test_validate_rejects_question_without_correct_option():
    raw = _question_bank()
    for option in raw["questions"][0]["options"]:
        option.pop("answer", None)
        option["distractor"] = "都没有正确答案"
    points = [parse_card(_rule_card())]
    problems = validate_seed(points, parse_question_bank(raw))
    assert any("G-A01-L1-01" in item and "正确项" in item for item in problems)


def test_validate_rejects_multiple_correct_options():
    raw = _question_bank()
    raw["questions"][0]["options"][0]["answer"] = True
    points = [parse_card(_rule_card())]
    problems = validate_seed(points, parse_question_bank(raw))
    assert any("G-A01-L1-01" in item for item in problems)


def test_validate_rejects_unknown_point_id():
    points = [parse_card(_rule_card())]
    raw = _question_bank()
    raw["point_id"] = "G-Z99"
    problems = validate_seed(points, parse_question_bank(raw))
    assert any("G-Z99" in item for item in problems)


def test_validate_accepts_bank_without_matching_card_when_card_missing():
    """题库指向的卡不存在是错误，必须报出来而不是静默丢弃。"""
    assert validate_seed([], parse_question_bank(_question_bank()))


# --- 目录级加载 ---


def _write_seed_dir(root: Path) -> Path:
    base = root / "grammar"
    (base / "cards").mkdir(parents=True)
    (base / "questions").mkdir(parents=True)

    card = _rule_card()
    (base / "cards" / "G-A01.json").write_text(
        json.dumps(card, ensure_ascii=False), encoding="utf-8"
    )
    # 故意用乱序文件名，验证排序按模块顺序而非文件名
    other = _contrast_card()
    (base / "cards" / "G-R03.json").write_text(
        json.dumps(other, ensure_ascii=False), encoding="utf-8"
    )
    (base / "questions" / "G-A01.json").write_text(
        json.dumps(_question_bank(), ensure_ascii=False), encoding="utf-8"
    )
    return base


def test_load_seed_grammar_counts(tmp_path: Path):
    points, questions, problems = load_seed_grammar(_write_seed_dir(tmp_path))
    assert problems == []
    assert [point.id for point in points] == ["G-R03", "G-A01"]  # 代词(R) 在形容词(A) 之前
    assert len(questions) == 2
    assert points[0].id in {"G-A01", "G-R03"}


def test_load_seed_grammar_order_index(tmp_path: Path):
    points, _, _ = load_seed_grammar(_write_seed_dir(tmp_path))
    assert [point.order_index for point in points] == [0, 1]


def test_load_seed_grammar_missing_dir_returns_empty(tmp_path: Path):
    points, questions, problems = load_seed_grammar(tmp_path / "nope")
    assert (points, questions) == ([], [])
    assert problems


def test_load_seed_grammar_skips_non_point_files(tmp_path: Path):
    """目录里的说明文件（如 README）不应被当成卡片。"""
    base = _write_seed_dir(tmp_path)
    (base / "cards" / "README.md").write_text("# 说明", encoding="utf-8")
    points, _, problems = load_seed_grammar(base)
    assert len(points) == 2
    assert problems == []


def test_seed_point_is_dataclass_instance(tmp_path: Path):
    points, _, _ = load_seed_grammar(_write_seed_dir(tmp_path))
    assert isinstance(points[0], SeedPoint)


# --- 种子目录探测（部署形态） ---


def test_default_seed_dir_honours_env_override(monkeypatch, tmp_path: Path):
    target = tmp_path / "custom-seed"
    target.mkdir()
    monkeypatch.setenv("GRAMMAR_SEED_DIR", str(target))
    assert default_seed_dir() == target


def test_default_seed_dir_falls_back_to_cwd_when_installed(monkeypatch, tmp_path: Path):
    """非 editable 安装：``__file__`` 在 site-packages，须回退到工作目录。

    现场症状：迁移 006 报 "未找到语法卡片目录 .../site-packages/../seeds"，
    建表成功但种子为空，线上大纲页空白。
    """
    monkeypatch.delenv("GRAMMAR_SEED_DIR", raising=False)
    installed_app = (
        tmp_path / "venv" / "lib" / "python3.12" / "site-packages" / "app"
    )
    installed_app.mkdir(parents=True)
    monkeypatch.setattr(
        seed_grammar, "__file__", str(installed_app / "seed_grammar.py")
    )

    workdir = tmp_path / "backend"
    (workdir / "seeds" / "grammar").mkdir(parents=True)
    monkeypatch.chdir(workdir)

    assert default_seed_dir() == workdir / "seeds" / "grammar"
