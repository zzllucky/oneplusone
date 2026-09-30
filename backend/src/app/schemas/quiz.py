from pydantic import BaseModel


class QuizQuestionItem(BaseModel):
    """题目：正确答案不下发，提交后返回 correct_index。"""

    question_id: int
    word_id: int
    type: str
    prompt: str
    options: list[str]


class QuizStartResponse(BaseModel):
    attempt_id: int
    questions: list[QuizQuestionItem]


class QuizAnswerRequest(BaseModel):
    question_id: int
    choice_index: int


class QuizAnswerResponse(BaseModel):
    """今日测验作答结果。

    ``added_to_wrong_words`` 仅在本次答错且首次入本时为 True；
    答对恒为 False —— 今日测验答对不会移除任何错题（FR-026）。
    """

    question_id: int
    is_correct: bool
    correct_index: int
    added_to_wrong_words: bool


class ReviewAnswerResponse(BaseModel):
    """错题专项练习作答结果。

    答对 → 连续答对次数 +1；达到 ``quiz_service.REVIEW_REMOVE_STREAK``（默认 2）
    才移出错题本（``removed_from_wrong_words`` 为 True，唯一删除路径）。
    未达阈值时 ``removed_from_wrong_words`` 为 False，``correct_streak``
    为当前连续答对次数，前端可提示"再答对 N 次即可移出"。
    """

    question_id: int
    is_correct: bool
    correct_index: int
    removed_from_wrong_words: bool
    # 本轮先答对移除、随后改答为错 → 重新入本（加入时间为本次答错）
    added_back_to_wrong_words: bool = False
    # 未达移出阈值时的当前连续答对次数；已移除为 0
    correct_streak: int = 0


class ArchiveAnswerResponse(BaseModel):
    """错题库专项练习作答结果。

    错题库是永久档案：答对不移除、次数不减（``removed_from_wrong_words`` 恒为 False）；
    答错只累加 ``archive_wrong_count``，同时把该词放回错题本待复习队列。
    """

    question_id: int
    is_correct: bool
    correct_index: int
    removed_from_wrong_words: bool = False
    # 答错时该词是否新进入错题本
    added_to_wrong_words: bool = False
    # 该词在错题库中的累计错误次数
    archive_wrong_count: int = 0


class QuizFinishResponse(BaseModel):
    attempt_id: int
    total_count: int
    correct_count: int
    wrong_count: int
    accuracy: float
    duration_seconds: int
    new_wrong_words: list[int]


class ReviewFinishResponse(BaseModel):
    attempt_id: int
    total_count: int
    correct_count: int
    wrong_count: int
    accuracy: float
    duration_seconds: int
    remaining_wrong_count: int


class ArchiveFinishResponse(BaseModel):
    attempt_id: int
    total_count: int
    correct_count: int
    wrong_count: int
    accuracy: float
    duration_seconds: int
    # 错题库总量（不因练习减少）
    archive_total: int
    # 错题本剩余数量
    remaining_wrong_count: int
