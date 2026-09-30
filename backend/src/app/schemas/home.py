from pydantic import BaseModel


class HomeUser(BaseModel):
    id: int
    login_name: str
    nickname: str


class HomeToday(BaseModel):
    study_date: str | None
    total_count: int
    viewed_count: int
    all_viewed: bool
    quiz_unlocked: bool


class RoundProgress(BaseModel):
    """当前轮次与进度（FR-006 / FR-013 / FR-015）。

    - ``learned_count``: 本轮已学（已进入当日集合）的单词数，按取词游标推算；
    - ``pending_quiz``: 本轮单词已学完、但当日测验尚未完成 → 该轮暂不计入已完成。
    """

    round_no: int
    learned_count: int
    total_count: int
    pending_quiz: bool


class HomeSummary(BaseModel):
    user: HomeUser
    daily_goal: int
    today: HomeToday
    wrong_word_count: int
    # 错题库（永久档案）累计条数
    archive_word_count: int = 0
    # 已完成词库学习的轮数（FR-005）
    completed_rounds: int = 0
    # 当前进行中轮次的进度（无进行中轮次时为 None）
    current_round: RoundProgress | None = None
