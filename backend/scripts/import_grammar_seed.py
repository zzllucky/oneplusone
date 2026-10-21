"""语法种子（``seeds/grammar``）幂等导入脚本。

用法::

    cd backend
    uv run python scripts/import_grammar_seed.py
    uv run python scripts/import_grammar_seed.py --dir /opt/1plus1/backend/seeds/grammar

迁移 ``006`` 建表后会自动导入；本脚本用于下列情况手动补齐 / 重导：

- 后端以非 editable 方式安装，seed 目录不在默认探测位置（可用 ``--dir`` 指定）
- 迁移已执行但种子缺失，需要补导
- 教研内容更新后重新导入

按主键 upsert，可重复执行，不会删除用户学习记录。

退出码：0 = 成功，1 = 目录缺失或种子校验失败。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.db import engine  # noqa: E402
from app.seed_grammar import (  # noqa: E402
    default_seed_dir,
    import_grammar,
    load_seed_grammar,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="导入语法知识点与题库（幂等）")
    parser.add_argument("--dir", default=None, help="seeds/grammar 目录，默认自动探测")
    args = parser.parse_args()

    base = Path(args.dir) if args.dir else default_seed_dir()
    if not base.is_dir():
        print(f"种子目录不存在: {base}", file=sys.stderr)
        return 1

    points, questions, problems = load_seed_grammar(base)
    if problems:
        print("种子校验失败：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    if engine is None:
        print("数据库未初始化", file=sys.stderr)
        return 1

    with engine.begin() as conn:
        added_points, added_questions, written_options = import_grammar(
            conn, points, questions
        )

    print(f"目录: {base}")
    print(
        f"知识点 {len(points)}（新增 {added_points}） / "
        f"题目 {len(questions)}（新增 {added_questions}） / "
        f"选项 {written_options}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
