"""学习活动时间线路由（#59）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.history import HistoryEventOut
from services import history_service

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[HistoryEventOut])
def get_history(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return history_service.get_history(db, user, limit)
