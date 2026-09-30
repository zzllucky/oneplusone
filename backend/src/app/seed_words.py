"""内置词表种子的统一格式解析。

统一格式（每行一条）::

    单词 | 词性.释义 [词性.释义…] | 例句

示例::

    the | art. 指已提到或易领会到的人或事物 | I have an apple and the apple is red. 我有一个苹果，它是红的。
    connect | v.(使)连接；与……有联系 | We are waiting for the telephone to be connected. 我们在等待电话接通。

兼容旧格式（仅一个 ``|``）::

    ability n.能力；才能 | have the ability to do 有能力做

规则：
- 空行、``#`` 注释行、``====组名====`` 分组行忽略
- **新格式**（≥2 个 ``|``）：第 1 段单词、第 2 段释义、其余各段合并为例句
- **旧格式**（1 个 ``|``）：``|`` 左侧为 ``单词 + 词性.释义`` 片段，右侧为短语
- 单词大小写不敏感去重，重复保留首次出现
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PHRASE_SEP = "；"
WORD_SEP = " | "
GROUP_LINE = re.compile(r"^=+\s*(.*?)\s*=+$")
COMMENT_LINE = re.compile(r"^#")
# 词性部分仅含 ASCII（可含 / . 空格与多词，如 adj./pron.、modal v.），释义以中文开头
POS_SEGMENT = re.compile(r"^([A-Za-z][A-Za-z./& ]*\.)([^\x00-\x7F].*)$")
BARE_POS = re.compile(r"^[A-Za-z]+$")
SPELLING = re.compile(r"^[A-Za-z][A-Za-z'\-. ]*$")
HAS_CJK = re.compile(r"[^\x00-\x7F]")
# 释义退化为纯词性（源数据缺中文释义），如 "n."
BARE_MEANING = re.compile(r"^[A-Za-z][A-Za-z./& ]*\.?$")

# 全角/弯引号与不换行连字符等易混字符归一，避免同一词条出现两种写法
_TRANSLATIONS = {
    ord("’"): "'",
    ord("‘"): "'",
    ord("“"): '"',
    ord("”"): '"',
    ord("　"): " ",
    ord(" "): " ",
    ord("‑"): "-",  # U+2011 不换行连字符：hard‑working / e‑mail
}


def normalize(text: str) -> str:
    """字符归一 + 空白折叠。"""
    return re.sub(r"\s+", " ", text.translate(_TRANSLATIONS)).strip()


@dataclass(frozen=True)
class SeedWord:
    """一条词表记录。"""

    spelling: str
    meaning_zh: str  # 形如 "v.(使)连接；与……有联系"
    phrase: str | None = None  # 例句（英文 + 中文）
    phonetic: str | None = None

    def to_line(self) -> str:
        """回写为统一格式的一行。"""
        line = f"{self.spelling}{WORD_SEP}{self.meaning_zh}"
        if self.phrase:
            line += f"{WORD_SEP}{self.phrase}"
        return line

    def to_row(self) -> dict:
        return {
            "spelling": self.spelling,
            "meaning_zh": self.meaning_zh,
            "phrase": self.phrase,
            "phonetic": self.phonetic,
        }


def _merge_multiword_pos(tokens: list[str]) -> list[str]:
    """合并跨空格的词性，如 ``modal`` + ``v.能`` → ``modal v.能``。"""
    merged: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        if following and BARE_POS.match(token) and POS_SEGMENT.match(following):
            merged.append(f"{token} {following}")
            index += 2
            continue
        merged.append(token)
        index += 1
    return merged


def _parse_segments(tokens: list[str]) -> tuple[str, str | None]:
    """把 ``词性.释义`` 片段拼成 meaning_zh；无法识别的片段返回问题说明。"""
    segments: list[str] = []
    problem: str | None = None
    for token in _merge_multiword_pos(tokens):
        matched = POS_SEGMENT.match(token)
        if matched:
            segments.append(f"{matched.group(1)}{matched.group(2)}")
            continue
        if segments:
            # 形如 "n.牛奶 v.挤 奶"（误空格）→ 并入上一段释义
            segments[-1] = f"{segments[-1]} {token}"
        else:
            problem = f"缺少词性: {token}"
    return " ".join(segments), problem


def _clean_spelling(raw: str) -> str:
    """取单词段的主写法：``a / an`` → ``a``，``telephone/phone number`` → ``telephone``。

    保留缩写中的句点（``A.M.``），仅去掉首尾逗号 / 分号。
    """
    head = raw.split("/")[0].strip().strip(",;；")
    return normalize(head)


def _parse_new_format(parts: list[str]) -> tuple[SeedWord | None, str | None]:
    """新格式：``单词 | 释义 | 例句[ | 例句中文]``。"""
    spelling = _clean_spelling(parts[0])
    if not spelling:
        return None, "空词条"
    if not SPELLING.match(spelling):
        return None, f"单词格式异常: {parts[0]}"

    meaning_zh = normalize(parts[1])
    if not meaning_zh:
        return None, f"{spelling}: 缺少释义"
    if not HAS_CJK.search(meaning_zh) and not BARE_MEANING.match(meaning_zh):
        return None, f"{spelling}: 释义缺少中文"

    # 例句可能被 `|` 拆成英文与中文两段，合并为一条
    phrase = normalize(" ".join(parts[2:])) or None
    return SeedWord(spelling=spelling, meaning_zh=meaning_zh, phrase=phrase), None


def _parse_legacy_format(parts: list[str]) -> tuple[SeedWord | None, str | None]:
    """旧格式：``单词 词性.释义… | 短语1；短语2``。"""
    left = parts[0].strip()
    tokens = left.split()
    if not tokens:
        return None, "空词条"

    spelling = tokens[0].strip(".,;；")
    if not SPELLING.match(spelling):
        return None, f"单词格式异常: {left}"

    meaning_zh, problem = _parse_segments(tokens[1:])
    if problem:
        return None, f"{spelling}: {problem}"
    if not meaning_zh:
        return None, f"{spelling}: 缺少“词性.释义”"

    phrases = [item.strip() for item in parts[1].split(PHRASE_SEP) if item.strip()]
    phrase = PHRASE_SEP.join(phrases) or None

    return SeedWord(spelling=spelling, meaning_zh=meaning_zh, phrase=phrase), None


def parse_line(raw: str) -> tuple[SeedWord | None, str | None]:
    """解析单行。返回 ``(词条, 问题描述)``；忽略行返回 ``(None, None)``。"""
    line = normalize(raw)
    if not line or COMMENT_LINE.match(line):
        return None, None

    if GROUP_LINE.match(line):
        return None, None

    parts = [part.strip() for part in line.split("|")]
    if len(parts) >= 3:
        return _parse_new_format(parts)
    # 1 段（单词 + 释义，无短语）或 2 段（旧格式）都按旧格式解析
    return _parse_legacy_format([parts[0], parts[1] if len(parts) == 2 else ""])


def parse_seed_text(text: str) -> tuple[list[SeedWord], list[str]]:
    """解析整段文本，返回 ``(去重后的词条, 问题描述列表)``。"""
    words: list[SeedWord] = []
    problems: list[str] = []
    seen: set[str] = set()

    for number, raw in enumerate(text.splitlines(), start=1):
        word, problem = parse_line(raw)
        if problem:
            problems.append(f"第 {number} 行 {problem}")
            continue
        if word is None:
            continue
        key = word.spelling.lower()
        if key in seen:
            problems.append(f"第 {number} 行 spelling 重复（已忽略）: {word.spelling}")
            continue
        seen.add(key)
        words.append(word)

    return words, problems


def load_seed_words(path: str | Path) -> list[SeedWord]:
    """读取词表文件；文件缺失返回空列表（迁移可安全跳过）。"""
    file_path = Path(path)
    if not file_path.exists():
        print(f"[seed] 未找到词表文件 {file_path}，跳过导入")
        return []

    text = file_path.read_text(encoding="utf-8-sig")
    words, problems = parse_seed_text(text)
    for item in problems[:50]:
        print(f"[seed] {item}")
    print(f"[seed] 解析 {file_path.name}：有效 {len(words)} 条，问题 {len(problems)} 条")
    return words


def render_seed_text(
    words: list[SeedWord], groups: list[tuple[int, str]] | None = None
) -> str:
    """回写为统一格式文本；``groups`` 为 ``(起始序号, 组名)``，作为注释保留。"""
    lines: list[str] = []
    comments = {index: name for index, name in (groups or [])}
    for index, word in enumerate(words):
        if index in comments:
            lines.append(f"# {comments[index]}")
        lines.append(word.to_line())
    return "\n".join(lines) + "\n"
