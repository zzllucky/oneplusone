"""词表种子体检脚本。

校验 ``seeds/words.txt``（统一格式 ``单词 | 词性.释义 | 例句``）：
1. 每行可解析为 单词 + 释义（旧格式要求至少一个 ``词性.释义`` 片段）
2. spelling 全局唯一（大小写不敏感）且非空
3. 条数达到下限（默认 150，可用环境变量 MIN_WORD_COUNT 覆盖）

退出码：0 = 通过，1 = 存在问题。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.seed_words import load_seed_words  # noqa: E402

DEFAULT_SEED = Path(__file__).resolve().parents[1] / "seeds" / "words.txt"


def validate(path: Path, min_count: int) -> list[str]:
    problems: list[str] = []

    if not path.exists():
        return [f"词表文件不存在: {path}"]

    words = load_seed_words(path)
    seen: set[str] = set()
    for word in words:
        key = word.spelling.lower()
        if key in seen:
            problems.append(f"spelling 重复: {word.spelling}")
        seen.add(key)
        if not word.meaning_zh:
            problems.append(f"{word.spelling} 缺少 meaning_zh")

    if len(words) < min_count:
        problems.append(f"词表条数不足: {len(words)} < {min_count}")

    with_phrase = sum(1 for word in words if word.phrase)
    print(f"[seed] 文件={path}")
    print(
        f"[seed] 条数={len(words)}  唯一 spelling={len(seen)}  "
        f"含短语={with_phrase}  下限={min_count}"
    )
    return problems


def main() -> int:
    seed_path = Path(os.environ.get("WORDS_SEED_PATH", DEFAULT_SEED))
    min_count = int(os.environ.get("MIN_WORD_COUNT", "150"))

    problems = validate(seed_path, min_count)
    if problems:
        print(f"[seed] 发现 {len(problems)} 个问题:")
        for item in problems[:50]:
            print(f"  - {item}")
        return 1

    print("[seed] 校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
