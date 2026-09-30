"""FastAPI 应用装配。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    auth,
    home,
    pronounce,
    quiz,
    settings as settings_api,
    study,
    summary,
    wrong_words,
)
from app.config import settings
from app.errors import AppError, ErrorResponse
from app.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("app.main")

app = FastAPI(title="中考英语单词学习测验与错题本", version="0.1.0")


class SPAStaticFiles(StaticFiles):
    """前端静态资源 + SPA 回退。

    前端使用 history 路由（``/home``、``/wrong-words`` 等），直接访问或刷新这些
    路径时服务器上并没有对应文件，需要回退到 ``index.html``，否则会返回 404 JSON。
    仅对"看起来像页面路径"的请求回退：带扩展名的资源（js/css/ico…）与
    ``/api/*`` 仍按 404 处理，避免把 HTML 当成脚本或接口响应返回。
    """

    def _is_page_path(self, path: str) -> bool:
        # Windows 下 Starlette 传入的路径分隔符为反斜杠，先统一成正斜杠
        normalized = path.replace("\\", "/").strip("/")
        if not normalized or normalized == "api" or normalized.startswith("api/"):
            return False
        suffix = Path(normalized).suffix
        return suffix in ("", ".html")

    def _index_or_404(self):
        index = Path(self.directory) / "index.html"
        if index.exists():
            return FileResponse(index)
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return self._index_or_404() if self._is_page_path(path) else JSONResponse(
                status_code=404, content={"detail": "Not Found"}
            )
        if getattr(response, "status_code", 200) == 404 and self._is_page_path(path):
            return self._index_or_404()
        return response


@app.exception_handler(AppError)
async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content=exc.payload().model_dump()
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    payload = ErrorResponse(
        error={"code": "validation_error", "message": "请求参数不合法"}
    )
    return JSONResponse(status_code=422, content=payload.model_dump())


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(home.router, prefix="/api")
app.include_router(study.router, prefix="/api")
app.include_router(quiz.router, prefix="/api")
app.include_router(wrong_words.router, prefix="/api")
app.include_router(pronounce.router, prefix="/api")
app.include_router(summary.router, prefix="/api")

static_dir = Path(settings.static_dir)
if static_dir.exists():
    app.mount(
        "/", SPAStaticFiles(directory=str(static_dir), html=True), name="frontend"
    )
    logger.info("已挂载前端静态目录: %s", static_dir)
