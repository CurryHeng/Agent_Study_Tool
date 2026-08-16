"""知识图谱路由（#58）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.knowledge_graph import KnowledgeGraphOut
from services import knowledge_graph_service

router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])


@router.get("", response_model=KnowledgeGraphOut)
def get_knowledge_graph(
    workbook_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return knowledge_graph_service.get_knowledge_graph(db, user, workbook_id)
