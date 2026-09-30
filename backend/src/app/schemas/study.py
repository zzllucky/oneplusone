import datetime as dt

from pydantic import BaseModel

from app.schemas.home import RoundProgress


class StudyWordItem(BaseModel):
    word_id: int
    spelling: str
    meaning_zh: str
    phrase: str | None = None
    phonetic: str | None = None
    order_index: int
    viewed_at: dt.datetime | None = None


class TodayStudyResponse(BaseModel):
    study_date: str
    total_count: int
    viewed_count: int
    all_viewed: bool
    quiz_unlocked: bool
    library_exhausted: bool
    items: list[StudyWordItem]
    # 当前轮次与进度（FR-006 / FR-013 / FR-015）
    round: RoundProgress | None = None


class ViewWordResponse(BaseModel):
    word_id: int
    viewed_count: int
    total_count: int
    all_viewed: bool
    quiz_unlocked: bool
