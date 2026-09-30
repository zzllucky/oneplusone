"""首页摘要接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.home import HomeSummary
from app.services import home_service

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/summary", response_model=HomeSummary)
def summary(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> HomeSummary:
    return HomeSummary(**home_service.summary(db, user))
