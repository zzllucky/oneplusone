import datetime as dt

from pydantic import BaseModel


class WrongWordItem(BaseModel):
    """错题本条目：待复习队列，连续答对达标后移出。"""

    word_id: int
    spelling: str
    meaning_zh: str
    phrase: str | None = None
    phonetic: str | None = None
    added_at: dt.datetime
    # 累计答错次数
    wrong_count: int = 1
    # 当前连续答对次数（达到阈值即移出，归零后重新累计）
    correct_streak: int = 0


class WrongWordListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[WrongWordItem]


class WrongArchiveItem(BaseModel):
    """错题库条目：永久档案，只存错误次数、不存时间、永不移除。"""

    word_id: int
    spelling: str
    meaning_zh: str
    phrase: str | None = None
    phonetic: str | None = None
    wrong_count: int = 1


class WrongArchiveListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    sort: str
    items: list[WrongArchiveItem]
