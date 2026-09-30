"""统一格式词表解析器的单元测试。

覆盖两种格式：
- 新格式（≥2 个 ``|``）：``单词 | 词性.释义 | 例句``
- 旧格式（1 个 ``|``）：``单词 词性.释义 | 短语1；短语2``
"""

from __future__ import annotations

import pytest

from app.seed_words import (
    SeedWord,
    parse_line,
    parse_seed_text,
    render_seed_text,
)

pytestmark = pytest.mark.unit


# --- 新格式：单词 | 释义 | 例句 ---


def test_parse_new_format_with_example():
    word, problem = parse_line(
        "the | art. 指已提到或易领会到的人或事物 | I have an apple and the apple is red. 我有一个苹果，它是红的。"
    )
    assert problem is None
    assert word == SeedWord(
        spelling="the",
        meaning_zh="art. 指已提到或易领会到的人或事物",
        phrase="I have an apple and the apple is red. 我有一个苹果，它是红的。",
    )


def test_parse_new_format_example_split_by_pipe():
    """例句的英文与中文被 ``|`` 分隔时合并为一条。"""
    word, problem = parse_line(
        "connect | v.(使)连接；与……有联系 | We are waiting for the telephone to be connected. | 我们在等待电话接通。"
    )
    assert problem is None
    assert word.spelling == "connect"
    assert word.phrase == (
        "We are waiting for the telephone to be connected. 我们在等待电话接通。"
    )


def test_parse_new_format_missing_example_is_allowed():
    word, problem = parse_line("hello | int.你好 |")
    assert problem is None
    assert word.phrase is None


def test_spelling_with_slash_takes_first_variant():
    word, problem = parse_line("a / an | art. 一(人、事、物) | We can find an umbrella in a box.")
    assert problem is None
    assert word.spelling == "a"


def test_non_breaking_hyphen_is_normalized():
    word, problem = parse_line("hard‑working | adj.勤勉的 | He is hard‑working.")
    assert problem is None
    assert word.spelling == "hard-working"


def test_spelling_with_dots_is_allowed():
    word, problem = parse_line("A.M. | 上午 | We leave at 10 A.M.")
    assert problem is None
    assert word.spelling == "A.M."


def test_bare_pos_meaning_is_accepted():
    """源数据缺中文释义（如 ``weight | n. |``）时保留词条而非丢弃。"""
    word, problem = parse_line("weight | n. | Bananas are sold by weight. 香蕉按重量出售。")
    assert problem is None
    assert word.spelling == "weight"
    assert word.meaning_zh == "n."


def test_new_format_without_meaning_is_reported():
    word, problem = parse_line("hello |  | hi")
    assert word is None
    assert problem and "缺少释义" in problem


# --- 旧格式兼容 ---


def test_parse_single_pos_and_phrases():
    word, problem = parse_line(
        "about prep.关于；大约 | talk about 谈论；think about 思考"
    )
    assert problem is None
    assert word == SeedWord(
        spelling="about",
        meaning_zh="prep.关于；大约",
        phrase="talk about 谈论；think about 思考",
    )


def test_parse_multi_pos():
    word, problem = parse_line("act v.行动；表演 n.行为 | act as 充当")
    assert problem is None
    assert word.meaning_zh == "v.行动；表演 n.行为"


def test_parse_multiword_pos():
    word, problem = parse_line("can modal v.能；可以 n.罐头 | can't wait to do 迫不及待做")
    assert problem is None
    assert word.meaning_zh == "modal v.能；可以 n.罐头"


def test_parse_slash_pos():
    word, problem = parse_line("all adj./pron.全部 | all over the world 全世界")
    assert problem is None
    assert word.meaning_zh == "adj./pron.全部"


def test_missing_phrase_is_allowed():
    word, problem = parse_line("hello int.你好")
    assert problem is None
    assert word.phrase is None


def test_group_and_comment_lines_are_ignored():
    assert parse_line("========第1组========") == (None, None)
    assert parse_line("# 第1组") == (None, None)
    assert parse_line("") == (None, None)


def test_missing_pos_is_reported():
    word, problem = parse_line("ability 能力 | do sth")
    assert word is None
    assert problem and "缺少" in problem


def test_duplicate_spelling_keeps_first():
    words, problems = parse_seed_text(
        "ability n.能力 | do\nABILITY n.能力（重复） | do again\n"
    )
    assert len(words) == 1
    assert words[0].spelling == "ability"
    assert len(problems) == 1


def test_render_roundtrip_new_format():
    text = (
        "the | art. 指已提到或易领会到的人或事物 | I have an apple. 我有一个苹果。\n"
    )
    words, problems = parse_seed_text(text)
    assert problems == []
    assert render_seed_text(words) == text


def test_curly_apostrophe_is_normalized():
    word, _ = parse_line("mind v.介意 | change one’s mind 改变想法")
    assert word.phrase == "change one's mind 改变想法"
