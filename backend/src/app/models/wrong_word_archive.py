"""wrong_word_archive —— 错题库（永久档案）。

与错题本（``wrong_words``）的区别：
- 只累计错误次数，**不记录任何时间**；
- **永不移除**：今日测验答对、专项练习答对都不会删除本表记录。

新增只发生在答错路径（``services/wrong_word_service.touch_wrong``），
本表没有任何删除入口。
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WrongWordArchive(Base):
    __tablename__ = "wrong_word_archive"
    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_wrong_word_archive"),
        Index("ix_wrong_word_archive_user", "user_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    word_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False
    )
    # 累计答错次数
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
