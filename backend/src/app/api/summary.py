"""学习日历总结接口（只读）：月历与单日明细。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.summary import DaySummary, MonthSummary
from app.services import summary_service

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("/month", response_model=MonthSummary)
def month(
    month: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthSummary:
    """当月（或指定月份）每日着色、月度总计与连续天数。"""
    return MonthSummary(**summary_service.month_summary(db, user.id, month))


@router.get("/day", response_model=DaySummary)
def day(
    date: str = Query(..., description="目标日期 YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DaySummary:
    """某一天的四项明细；无记录时返回 has_record=false（不是 404）。"""
    return DaySummary(**summary_service.day_summary(db, user.id, date))
