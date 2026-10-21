"""语法种子（``seeds/grammar``）的解析与导入。

目录结构::

    seeds/grammar/cards/G-A01.json      一张卡 = 一个知识点（含 3 道卡内检测 check）
    seeds/grammar/questions/G-A01.json  该知识点的题库（L1/L2/L3 各 2 题）

解析规则：
- 卡片的教研内容（guess / rule / contrast / guess_callback）整体进 ``payload``
- 卡片的 ``check`` 与题库的 ``questions`` 都解析成题目，用 ``source`` 区分
- 选项的答案标记有两种写法：正确项 ``answer: true``，干扰项 ``distractor: 错因``
- 合并卡（如 G-T09 覆盖 G-T10/G-T11）用 ``covers`` 记录被合并的知识点 id

导入按主键幂等：已存在则更新，不存在则插入（R-001 / R-009）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa

# 大纲模块展示顺序（与 syllabus.md 一致）
MODULE_ORDER = ("T", "V", "F", "N", "R", "U", "B", "A", "D", "O", "S", "C")

CARDS_SUBDIR = "cards"
QUESTIONS_SUBDIR = "questions"
CARD_FILE_GLOB = "G-*.json"

SOURCE_CARD = "card"  # 卡内学后检测
SOURCE_BANK = "bank"  # 题库练习

VALID_LEVELS = ("L1", "L2", "L3")
# 进 payload 的教学字段（其余字段进独立列或题目表）
PAYLOAD_KEYS = ("guess", "rule", "contrast", "guess_callback")


def default_seed_dir() -> Path:
    """``backend/seeds/grammar`` 的默认位置。"""
    return Path(__file__).resolve().parents[2] / "seeds" / "grammar"


@dataclass(frozen=True)
class SeedOption:
    """一个选项。"""

    key: str
    text: str
    is_correct: bool
    feedback: str | None = None  # 错因 / 选项反馈


@dataclass(frozen=True)
class SeedQuestion:
    """一道题。"""

    id: str
    point_id: str
    source: str
    level: str
    stem: str
    explanation: str
    error_tag: str | None
    options: list[SeedOption] = field(default_factory=list)
    order_index: int = 0


@dataclass(frozen=True)
class SeedPoint:
    """一个语法知识点（卡片），自带卡内检测题。"""

    id: str
    module: str
    module_name: str
    title: str
    depth: str
    card_type: str
    payload: dict
    covers: list[str]
    order_index: int = 0
    questions: list[SeedQuestion] = field(default_factory=list)


def _read_json(path: Path) -> dict | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"[seed] 读取失败 {path.name}: {error}")
        return None
    return raw if isinstance(raw, dict) else None


def _is_correct(raw: dict) -> bool:
    """兼容两种答案写法：``answer: true`` 与 ``answer: "A"``。"""
    answer = raw.get("answer")
    if isinstance(answer, str):
        return answer.strip().upper() == str(raw.get("key", "")).strip().upper()
    return bool(answer)


def _parse_options(raw_options: list | None) -> list[SeedOption]:
    options: list[SeedOption] = []
    for raw in raw_options or []:
        if not isinstance(raw, dict):
            continue
        options.append(
            SeedOption(
                key=str(raw.get("key", "")),
                text=str(raw.get("text", "")),
                is_correct=_is_correct(raw),
                feedback=raw.get("distractor") or raw.get("feedback") or None,
            )
        )
    return options


def _parse_question(
    raw: dict, point_id: str, source: str, order_index: int
) -> SeedQuestion:
    return SeedQuestion(
        id=str(raw.get("id", "")),
        point_id=point_id,
        source=source,
        level=str(raw.get("level", "L1")),
        stem=str(raw.get("stem", "")),
        explanation=str(raw.get("explanation", "")),
        error_tag=raw.get("error_tag") or point_id,
        options=_parse_options(raw.get("options")),
        order_index=order_index,
    )


def parse_card(raw: dict) -> SeedPoint:
    """解析一张卡片文件。"""
    point_id = str(raw.get("id", ""))
    return SeedPoint(
        id=point_id,
        module=str(raw.get("module", "")),
        module_name=str(raw.get("module_name", "")),
        title=str(raw.get("title", "")),
        depth=str(raw.get("depth", "核心")),
        card_type=str(raw.get("type", "rule")),
        payload={key: raw[key] for key in PAYLOAD_KEYS if key in raw},
        covers=list(raw.get("covers") or [point_id]),
        questions=[
            _parse_question(item, point_id, SOURCE_CARD, index)
            for index, item in enumerate(raw.get("check") or [])
        ],
    )


def parse_question_bank(raw: dict) -> list[SeedQuestion]:
    """解析一个题库文件。"""
    point_id = str(raw.get("point_id", ""))
    return [
        _parse_question(item, point_id, SOURCE_BANK, index)
        for index, item in enumerate(raw.get("questions") or [])
    ]


def _sort_key(point: SeedPoint) -> tuple[int, str]:
    try:
        module_rank = MODULE_ORDER.index(point.module)
    except ValueError:
        module_rank = len(MODULE_ORDER)
    return (module_rank, point.id)


def validate_seed(points: list[SeedPoint], questions: list[SeedQuestion]) -> list[str]:
    """校验不变量，返回问题描述列表（空列表表示全部通过）。"""
    problems: list[str] = []
    known_points = {point.id for point in points}
    seen_ids: set[str] = set()

    all_questions: list[SeedQuestion] = []
    for point in points:
        all_questions.extend(point.questions)
    all_questions.extend(questions)

    for question in all_questions:
        if question.id in seen_ids:
            problems.append(f"{question.id}: 题目 id 重复")
        seen_ids.add(question.id)

        if question.point_id not in known_points:
            problems.append(
                f"{question.id}: point_id 无对应知识点卡片 {question.point_id}"
            )
        if question.level not in VALID_LEVELS:
            problems.append(f"{question.id}: 难度取值非法 {question.level}")
        if not question.stem:
            problems.append(f"{question.id}: 缺少题干")

        correct = [option for option in question.options if option.is_correct]
        if len(correct) != 1:
            problems.append(
                f"{question.id}: 正确项数量应为 1，实际 {len(correct)}"
            )
        if len(question.options) < 2:
            problems.append(f"{question.id}: 选项少于 2 个")

    return problems


def load_seed_grammar(
    base_dir: str | Path,
) -> tuple[list[SeedPoint], list[SeedQuestion], list[str]]:
    """读取语法种子目录，返回 ``(知识点, 题库题目, 问题列表)``。

    目录缺失返回空列表，迁移可安全跳过。
    """
    root = Path(base_dir)
    card_dir = root / CARDS_SUBDIR
    question_dir = root / QUESTIONS_SUBDIR

    if not card_dir.is_dir():
        print(f"[seed] 未找到语法卡片目录 {card_dir}，跳过导入")
        return [], [], [f"缺少卡片目录: {card_dir}"]

    points: list[SeedPoint] = []
    problems: list[str] = []
    for path in sorted(card_dir.glob(CARD_FILE_GLOB)):
        raw = _read_json(path)
        if raw is None:
            problems.append(f"无法解析卡片: {path.name}")
            continue
        points.append(parse_card(raw))

    points.sort(key=_sort_key)
    points = [
        SeedPoint(
            id=point.id,
            module=point.module,
            module_name=point.module_name,
            title=point.title,
            depth=point.depth,
            card_type=point.card_type,
            payload=point.payload,
            covers=point.covers,
            order_index=index,
            questions=point.questions,
        )
        for index, point in enumerate(points)
    ]

    bank: list[SeedQuestion] = []
    if question_dir.is_dir():
        for path in sorted(question_dir.glob(CARD_FILE_GLOB)):
            raw = _read_json(path)
            if raw is None:
                problems.append(f"无法解析题库: {path.name}")
                continue
            bank.extend(parse_question_bank(raw))
    else:
        print(f"[seed] 未找到语法题库目录 {question_dir}")

    problems.extend(validate_seed(points, bank))

    card_questions = sum(len(point.questions) for point in points)
    for item in problems[:50]:
        print(f"[seed] {item}")
    print(
        f"[seed] 解析 {root.name}：知识点 {len(points)} 个，"
        f"卡内检测 {card_questions} 道，题库 {len(bank)} 道，问题 {len(problems)} 条"
    )
    return points, bank, problems


def import_grammar(
    bind: sa.Connection | sa.Engine,
    points: list[SeedPoint],
    questions: list[SeedQuestion],
) -> tuple[int, int, int]:
    """把种子幂等写入三张表，返回 ``(知识点新增, 题目新增, 选项写入)``。

    知识点与题目按主键 upsert；选项采用"整题替换"（先删后插），
    保证重复导入不会累积重复选项。
    """
    if not points:
        return 0, 0, 0

    # 允许传入 Engine（脚本调用方便）：转成 Connection 后递归一次
    if isinstance(bind, sa.Engine):
        with bind.begin() as connection:
            return import_grammar(connection, points, questions)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    points_table = sa.table(
        "grammar_points",
        sa.column("id", sa.String),
        sa.column("module", sa.String),
        sa.column("module_name", sa.String),
        sa.column("title", sa.String),
        sa.column("depth", sa.String),
        sa.column("card_type", sa.String),
        sa.column("order_index", sa.Integer),
        sa.column("payload", sa.JSON),
        sa.column("covers", sa.JSON),
        sa.column("created_at", sa.DateTime),
    )
    questions_table = sa.table(
        "grammar_questions",
        sa.column("id", sa.String),
        sa.column("point_id", sa.String),
        sa.column("source", sa.String),
        sa.column("level", sa.String),
        sa.column("stem", sa.Text),
        sa.column("explanation", sa.Text),
        sa.column("error_tag", sa.String),
        sa.column("order_index", sa.Integer),
        sa.column("created_at", sa.DateTime),
    )
    options_table = sa.table(
        "grammar_options",
        sa.column("question_id", sa.String),
        sa.column("key", sa.String),
        sa.column("text", sa.Text),
        sa.column("is_correct", sa.Boolean),
        sa.column("feedback", sa.Text),
        sa.column("order_index", sa.Integer),
    )

    existing_points = {
        row[0] for row in bind.execute(sa.select(points_table.c.id))
    }
    point_inserts: list[dict] = []
    for point in points:
        payload_row = {
            "id": point.id,
            "module": point.module,
            "module_name": point.module_name,
            "title": point.title,
            "depth": point.depth,
            "card_type": point.card_type,
            "order_index": point.order_index,
            "payload": point.payload,
            "covers": point.covers,
            "created_at": now,
        }
        if point.id in existing_points:
            bind.execute(
                points_table.update()
                .where(points_table.c.id == point.id)
                .values(
                    module=payload_row["module"],
                    module_name=payload_row["module_name"],
                    title=payload_row["title"],
                    depth=payload_row["depth"],
                    card_type=payload_row["card_type"],
                    order_index=payload_row["order_index"],
                    payload=payload_row["payload"],
                    covers=payload_row["covers"],
                )
            )
        else:
            point_inserts.append(payload_row)
    if point_inserts:
        bind.execute(points_table.insert(), point_inserts)

    all_questions: list[SeedQuestion] = []
    for point in points:
        all_questions.extend(point.questions)
    all_questions.extend(questions)

    existing_questions = {
        row[0] for row in bind.execute(sa.select(questions_table.c.id))
    }
    question_inserts: list[dict] = []
    touched: list[str] = []
    for question in all_questions:
        row = {
            "id": question.id,
            "point_id": question.point_id,
            "source": question.source,
            "level": question.level,
            "stem": question.stem,
            "explanation": question.explanation,
            "error_tag": question.error_tag,
            "order_index": question.order_index,
            "created_at": now,
        }
        if question.id in existing_questions:
            bind.execute(
                questions_table.update()
                .where(questions_table.c.id == question.id)
                .values(
                    point_id=row["point_id"],
                    source=row["source"],
                    level=row["level"],
                    stem=row["stem"],
                    explanation=row["explanation"],
                    error_tag=row["error_tag"],
                    order_index=row["order_index"],
                )
            )
        else:
            question_inserts.append(row)
        touched.append(question.id)

    if question_inserts:
        bind.execute(questions_table.insert(), question_inserts)

    # 选项整题替换：只处理本次涉及的题目，避免清空全表
    option_rows: list[dict] = []
    for question in all_questions:
        for index, option in enumerate(question.options):
            option_rows.append(
                {
                    "question_id": question.id,
                    "key": option.key,
                    "text": option.text,
                    "is_correct": option.is_correct,
                    "feedback": option.feedback,
                    "order_index": index,
                }
            )

    for chunk_start in range(0, len(touched), 400):
        chunk = touched[chunk_start : chunk_start + 400]
        bind.execute(
            options_table.delete().where(options_table.c.question_id.in_(chunk))
        )
    if option_rows:
        for chunk_start in range(0, len(option_rows), 400):
            bind.execute(
                options_table.insert(), option_rows[chunk_start : chunk_start + 400]
            )

    return len(point_inserts), len(question_inserts), len(option_rows)


__all__ = [
    "CARDS_SUBDIR",
    "MODULE_ORDER",
    "PAYLOAD_KEYS",
    "QUESTIONS_SUBDIR",
    "SOURCE_BANK",
    "SOURCE_CARD",
    "VALID_LEVELS",
    "SeedOption",
    "SeedPoint",
    "SeedQuestion",
    "default_seed_dir",
    "import_grammar",
    "load_seed_grammar",
    "parse_card",
    "parse_question_bank",
    "validate_seed",
]
