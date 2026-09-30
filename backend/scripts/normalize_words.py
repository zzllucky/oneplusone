"""把任意来源的词表文本归一为统一格式 ``seeds/words.txt``。

用法::

    python scripts/normalize_words.py <源文件> [-o 输出文件]

统一格式：``单词 | 词性.释义 | 例句``（兼容旧格式 ``单词 词性.释义 | 短语1；短语2``）
- ``====第N组====`` 分组行保留为 ``# 第N组`` 注释
- 大小写不敏感去重（保留首次出现）
- 解析问题逐条打印，退出码 1 表示存在问题
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.seed_words import (  # noqa: E402
    GROUP_LINE,
    load_seed_words,
    render_seed_text,
)

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "seeds" / "words.txt"


def extract_groups(text: str) -> list[tuple[int, str]]:
    """提取分组注释（按分组前已解析出的词条数定位）。"""
    groups: list[tuple[int, str]] = []
    count = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        matched = GROUP_LINE.match(line)
        if matched:
            groups.append((count, matched.group(1) or "分组"))
            continue
        if line.startswith("#") or "|" not in line:
            continue
        count += 1
    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description="归一化为统一词表格式")
    parser.add_argument("source", help="源词表文本（如桌面导出的 a.txt）")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT), help="输出文件")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"[norm] 源文件不存在: {source}")
        return 1

    text = source.read_text(encoding="utf-8-sig")
    words = load_seed_words(source)
    if not words:
        print("[norm] 未解析出任何词条，已中止")
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_seed_text(words, extract_groups(text)), encoding="utf-8"
    )

    with_phrase = sum(1 for word in words if word.phrase)
    print(
        f"[norm] 输出 {output}：{len(words)} 条，"
        f"含短语 {with_phrase} 条，分组 {len(extract_groups(text))} 个"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
