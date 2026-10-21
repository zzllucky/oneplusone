"""语法模块接口模型（Pydantic v2）。

字段与错误码以 specs/006-grammar-study/contracts/api.md 为唯一契约来源。
本模块不接收 ORM 对象（不使用 ``from_attributes``），服务层返回 dict 后由
``XxxResponse(**result)`` 组装。

答案保护：所有出题模型（``GrammarQuestionItem`` / ``GrammarOptionItem``）只含
``key`` 与 ``text``，不含 ``is_correct`` / ``explanation`` / ``feedback``。
"""

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field


class GrammarOptionItem(BaseModel):
    """选项：作答前只下发键与文本（FR-007）。"""

    key: str
    text: str


class GrammarQuestionItem(BaseModel):
    """题目：题干 + 选项，不含任何答案信息。"""

    question_id: str
    level: str
    stem: str
    options: list[GrammarOptionItem]


class GrammarPointItem(BaseModel):
    """大纲中的知识点条目。"""

    id: str
    title: str
    depth: str
    card_type: str
    status: str
    has_wrong: bool
    question_count: int


class GrammarOutlineModule(BaseModel):
    """大纲模块分组。"""

    module: str
    module_name: str
    points: list[GrammarPointItem]


class GrammarOutlineResponse(BaseModel):
    """语法大纲：汇总计数 + 按模块分组的知识点。"""

    total_points: int
    mastered_count: int
    wrong_count: int
    modules: list[GrammarOutlineModule]


class GrammarPointDetail(BaseModel):
    """知识点学卡头部信息。"""

    id: str
    module: str
    module_name: str
    title: str
    depth: str
    card_type: str
    status: str
    has_wrong: bool


class GrammarPointDetailResponse(BaseModel):
    """知识点学卡：头部 + 清洗后的教研内容 + 卡内检测题。"""

    point: GrammarPointDetail
    payload: dict[str, Any]
    check_questions: list[GrammarQuestionItem]


class GrammarViewResponse(BaseModel):
    """标记已学（打开学卡）结果。"""

    point_id: str
    status: str
    studied_at: dt.datetime | None


class GrammarGuessRequest(BaseModel):
    """提交"猜一猜"所选选项键。"""

    choice_key: str = Field(min_length=1, max_length=2)


class GrammarGuessResponse(BaseModel):
    """猜一猜反馈：作答之后才下发，不构成答案泄露。"""

    point_id: str
    choice_key: str
    feedback: str


class GrammarPracticeStartRequest(BaseModel):
    """发起题库练习：``level`` 为空表示全部层级。"""

    level: str | None = None


class AttemptStartResponse(BaseModel):
    """开始一轮（学后检测 / 题库练习）的响应。"""

    attempt_id: int
    source: str
    point_id: str
    questions: list[GrammarQuestionItem]


class GrammarAnswerRequest(BaseModel):
    question_id: str
    choice_key: str = Field(min_length=1, max_length=2)


class GrammarAttemptProgress(BaseModel):
    """本轮进度计数。"""

    total_count: int
    answered_count: int
    correct_count: int
    wrong_count: int


class GrammarAnswerResponse(BaseModel):
    """判分结果（学后检测与练习共用）。"""

    question_id: str
    is_correct: bool
    correct_key: str
    explanation: str
    feedback: str | None
    attempt: GrammarAttemptProgress
    added_to_wrong_points: bool
    removed_from_wrong_points: bool
    correct_streak: int


class GrammarFinishResponse(BaseModel):
    """结算结果。"""

    attempt_id: int
    source: str
    point_id: str
    total_count: int
    correct_count: int
    wrong_count: int
    accuracy: float
    duration_seconds: int
    mastered: bool
    status: str


class GrammarWrongPointItem(BaseModel):
    """语法错题本条目。"""

    point_id: str
    title: str
    module: str
    module_name: str
    wrong_count: int
    correct_streak: int
    added_at: dt.datetime
    last_wrong_at: dt.datetime


class GrammarWrongPointListResponse(BaseModel):
    total: int
    items: list[GrammarWrongPointItem]
