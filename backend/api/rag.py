"""RAG 检索路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.rag import RetrievalItem, RetrieveRequest
from services import rag_service

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/retrieve", response_model=list[RetrievalItem])
def retrieve(
    body: RetrieveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return rag_service.retrieve(
        db, user, body.workbook_id, body.query, body.knowledge_id, body.top_k
    )
