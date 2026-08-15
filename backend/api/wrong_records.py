"""错题本路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.wrong_record import WrongRecordOut, WrongRecordUpdate
from services import wrong_record_service

router = APIRouter(prefix="/api/wrong-records", tags=["wrong-records"])


@router.get("", response_model=list[WrongRecordOut])
def list_wrong_records(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return wrong_record_service.list_wrong_records(db, user)


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
