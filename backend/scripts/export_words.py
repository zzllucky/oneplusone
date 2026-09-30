"""把数据库中的词表导出为统一格式文本（``单词 | 词性.释义 | 例句``）。

用法::

    python scripts/export_words.py [输出路径]        # 默认 words_export.txt
    DB_PATH=/opt/1plus1/data/app.db python scripts/export_words.py bb.txt

导出的文件可直接作为词表源文件，用 ``scripts/normalize_words.py`` 回灌。
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

WORD_SEP = " | "


def export(db_path: Path, out_path: Path) -> int:
    if not db_path.exists():
        print(f"[export] 数据库不存在: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT spelling, meaning_zh, phrase FROM words ORDER BY id"
    ).fetchall()
    conn.close()

    lines: list[str] = []
    for row in rows:
        parts = [row["spelling"], row["meaning_zh"]]
        if row["phrase"]:
            parts.append(row["phrase"])
        lines.append(WORD_SEP.join(parts))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[export] {out_path}：共 {len(lines)} 条")
    return 0


def main() -> int:
    db_path = Path(os.environ.get("DB_PATH", "data/app.db"))
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("words_export.txt")
    return export(db_path, out_path)


if __name__ == "__main__":
    sys.exit(main())
