"""刷题路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.review import AnswerRequest, AnswerResponse, DueItem, ReviewCardOut
from services import review_service

router = APIRouter(prefix="/api", tags=["review"])


@router.post("/questions/{question_id}/answer", response_model=AnswerResponse)
def answer_question(
    question_id: int,
    body: AnswerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    out = review_service.answer_question(db, user, question_id, body)
    db.commit()
    return out


@router.get("/review/due", response_model=list[DueItem])
def get_due(
    limit: int = 20,
    favorites: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return review_service.get_due(db, user, limit, favorites)


@router.post("/review/{question_id}/favorite", response_model=ReviewCardOut)
def toggle_favorite(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    out = review_service.toggle_favorite(db, user, question_id)
    db.commit()
    return out
