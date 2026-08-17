"""题目路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.generation import GeneratedQuestion, GenerateRequest, GenerateResult
from schemas.question import (
    QuestionCreate,
    QuestionOut,
    QuestionPageOut,
    QuestionUpdate,
)
from services import generation_service, question_service, rag_service
from services.access import AccessError

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=list[QuestionOut] | QuestionPageOut)
def list_questions(
    workbook_id: int | None = None,
    page: int | None = None,
    page_size: int | None = None,
    with_total: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return question_service.list_questions(
        db, user, workbook_id, page, page_size, with_total
    )


@router.post("", status_code=201, response_model=QuestionOut)
def create_question(
    body: QuestionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    out = question_service.create_question(db, user, body)
    db.commit()
    return out


@router.post("/generate", response_model=GenerateResult)
def generate_questions(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    context = rag_service.build_context(db, user, body.workbook_id, body.knowledge_id)
    out = generation_service.generate_questions_with_review(
        db,
        user,
        body.workbook_id,
        body.type,
        body.count,
        body.knowledge_id,
        body.difficulty,
        context=context,
    )
    db.commit()
    return out


@router.get("/{question_id}", response_model=QuestionOut)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return question_service.get_question(db, user, question_id)


@router.post("/{question_id}/similar", response_model=GeneratedQuestion)
def generate_similar(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = generation_service.generate_similar(db, user, question_id)
    if result is None:
        raise AccessError(500, "生成相似题失败，请稍后再试")
    return result


@router.put("/{question_id}", response_model=QuestionOut)
def update_question(
    question_id: int,
    body: QuestionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    out = question_service.update_question(db, user, question_id, body)
    db.commit()
    return out


@router.delete("/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    question_service.delete_question(db, user, question_id)
    db.commit()
    return {"ok": True}
