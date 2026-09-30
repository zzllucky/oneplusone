"""发音接口（独立前缀 /api/pronounce）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_current_user
from app.models.user import User
from app.services.pronounce_service import fetch_pronunciation

router = APIRouter(prefix="/pronounce", tags=["pronounce"])


@router.get("/{word}")
def pronounce(word: str, user: User = Depends(get_current_user)) -> Response:
    content = fetch_pronunciation(word)
    return Response(
        content=content,
        media_type="audio/mpeg",
        # 发音结果不变，允许浏览器复用，重复点击不再回源
        headers={"Cache-Control": "private, max-age=86400"},
    )
