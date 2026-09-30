"""wrong_words —— 错题本。

删除规则（FR-031 / FR-038）：本表的 DELETE 只允许出现在
``services/quiz_service.record_review_answer`` 的"专项练习答对"分支。
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class WrongWord(Base):
    __tablename__ = "wrong_words"
    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_wrong_word"),
        Index("ix_wrong_words_user_added", "user_id", "added_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    word_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False
    )
    # 首次答错时间；重复答错不更新
    added_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    # 累计答错次数（每次答错 +1）
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 连续答对次数：达到 REVIEW_REMOVE_STREAK 才移出错题本，答错归零
    correct_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 最近一次答错时间（可为空：迁移前历史记录）
    last_wrong_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime, nullable=True, default=utcnow
    )
