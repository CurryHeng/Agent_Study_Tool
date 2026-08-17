"""刷题路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.review import (
    AnswerRequest,
    AnswerResponse,
    DueItem,
    GradeRequest,
    GradeResponse,
    ReviewCardOut,
)
from services import access, grading, review_service

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


@router.post("/questions/{question_id}/grade", response_model=GradeResponse)
def grade_question(
    question_id: int,
    body: GradeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """单独判分（不落库、不更新 FSRS）：供前端"上交"时即时展示权威判分结果。"""
    question = access.get_visible_question(db, user, question_id)
    is_correct = grading.grade_answer(question, body.user_answer)
    return GradeResponse(
        is_correct=is_correct,
        correct_answer=question.answer,
        analysis=question.analysis,
    )


@router.get("/review/due", response_model=list[DueItem])
def get_due(
    limit: int = 20,
    favorites: bool = False,
    include_all: bool = False,
    workbook_id: int | None = None,
    question_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return review_service.get_due(
        db, user, limit, favorites, include_all, workbook_id, question_id
    )


@router.post("/review/{question_id}/favorite", response_model=ReviewCardOut)
def toggle_favorite(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    out = review_service.toggle_favorite(db, user, question_id)
    db.commit()
    return out
