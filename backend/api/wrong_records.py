"""错题本路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.wrong_record import (
    WrongReasonAnalysis,
    WrongRecordOut,
    WrongRecordPageOut,
    WrongRecordUpdate,
)
from services import coach_service, wrong_record_service

router = APIRouter(prefix="/api/wrong-records", tags=["wrong-records"])


@router.get("", response_model=list[WrongRecordOut] | WrongRecordPageOut)
def list_wrong_records(
    knowledge_id: int | None = None,
    question_type: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    with_total: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return wrong_record_service.list_wrong_records(
        db, user, knowledge_id, question_type, page, page_size, with_total
    )


@router.put("/{record_id}", response_model=WrongRecordOut)
def update_wrong_record(
    record_id: int,
    body: WrongRecordUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    out = wrong_record_service.update_wrong_record(
        db, user, record_id, body.model_dump(exclude_unset=True)
    )
    db.commit()
    return out


@router.post("/{record_id}/analyze", response_model=WrongReasonAnalysis)
def analyze_wrong_record(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    out = coach_service.analyze_wrong_reason(db, user, record_id)
    db.commit()
    return out
