"""统一错误模型与错误码。

所有业务失败均以 ``AppError`` 抛出，由 ``main.py`` 的异常处理器转换为
``{"error": {"code": ..., "message": ...}}``，与 contracts/api.md 一致。
"""

from __future__ import annotations

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


ERROR_MESSAGES: dict[str, str] = {
    "invalid_credentials": "登录名或密码错误",
    "login_name_taken": "该登录名已被使用",
    "weak_password": "密码至少 6 位",
    "invalid_login_name": "登录名需为 3–20 位字母、数字或下划线",
    "invalid_nickname": "昵称需为 1–24 个字符",
    "unauthorized": "请先登录",
    "goal_out_of_range": "每日目标需为 1–200 之间的整数",
    "word_not_in_today_set": "该单词不在今日学习列表中",
    "quiz_locked": "请先完成今日全部单词浏览",
    "no_wrong_words": "错题本为空，暂无可练习的单词",
    "no_archive_words": "错题库为空，暂无可练习的单词",
    "attempt_not_found": "测验不存在或已结束",
    "question_not_found": "题目不存在",
    "attempt_already_finished": "该轮测验已结束",
    "pronunciation_unavailable": "暂无发音，已切换本地朗读",
    "validation_error": "请求参数不合法",
    "invalid_month": "月份格式需为 YYYY-MM",
    "invalid_date": "日期格式需为 YYYY-MM-DD",
}


class AppError(Exception):
    """业务异常：携带稳定的 error code 与 HTTP 状态码。"""

    def __init__(self, code: str, message: str | None = None, status_code: int = 400):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, code)
        self.status_code = status_code
        super().__init__(self.message)

    def payload(self) -> ErrorResponse:
        return ErrorResponse(error=ErrorDetail(code=self.code, message=self.message))
