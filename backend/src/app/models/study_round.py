"""study_rounds —— 学习轮次（词库循环学习）。

一个账号对词库的一次完整遍历 = 一轮。取词由 ``cursor_word_id`` 游标驱动：
``SELECT id FROM words WHERE id >= cursor ORDER BY id LIMIT goal``，
分配后游标推进到"下一个待分配单词"，因此**一轮内每个单词恰好出现一次**
且顺序与词库原顺序一致（FR-003 / FR-012）。

状态机（由 ``services/round_service`` 驱动）：

    进行中 → 已覆盖（covered_at 写入）→ 已完成（completed_at 写入）

- **已覆盖**：游标越过词库最后一个单词（该日单词已分配完）；
- **已完成**：已覆盖 **且** 轮末当日测验完成（FR-004）；
  次日补记（FR-014）同样写 ``completed_at``，但**不为该日伪造测验成绩**。

不变量：
1. 同一账号至多一行 ``completed_at IS NULL``（部分唯一索引保证）；
2. ``completed_at`` 非空 ⇒ ``covered_at`` 非空；
3. 一轮内 ``cursor_word_id`` 单调不减；跨轮时重置为词库最小 ``Word.id``；
4. 轮次推进**不删除任何历史数据**（FR-008）。
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StudyRound(Base):
    __tablename__ = "study_rounds"
    __table_args__ = (
        UniqueConstraint("user_id", "round_no", name="uq_study_rounds_user_round"),
        # 单账号单"进行中"轮次（SQLite 部分索引）
        Index(
            "uq_study_rounds_open",
            "user_id",
            unique=True,
            sqlite_where=text("completed_at IS NULL"),
        ),
        Index("ix_study_rounds_user_completed", "user_id", "completed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # 轮序号，同一账号内从 1 递增
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    # 下一个待分配单词 id，按 Word.id 升序推进；跨轮时重置为词库最小 id
    cursor_word_id: Mapped[int] = mapped_column(Integer, nullable=False)
    started_on: Mapped[dt.date] = mapped_column(Date, nullable=False)
    # 已覆盖时刻：游标越过词库最后一个单词
    covered_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    # 已完成时刻：已覆盖且轮末当日测验完成（含次日补记）
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
