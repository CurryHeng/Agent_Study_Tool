"""知识点路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.knowledge import KnowledgeCreate, KnowledgeOut, KnowledgeUpdate
from services import knowledge_service

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeOut])
def list_knowledge(
    workbook_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list:
    return knowledge_service.list_knowledge(db, user, workbook_id)


@router.post("", status_code=201, response_model=KnowledgeOut)
def create_knowledge(
    body: KnowledgeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    node = knowledge_service.create_knowledge(db, user, body)
    db.commit()
    return node


@router.get("/{knowledge_id}", response_model=KnowledgeOut)
def get_knowledge(
    knowledge_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return knowledge_service.get_knowledge(db, user, knowledge_id)


@router.put("/{knowledge_id}", response_model=KnowledgeOut)
def update_knowledge(
    knowledge_id: int,
    body: KnowledgeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    node = knowledge_service.update_knowledge(db, user, knowledge_id, body)
    db.commit()
    return node


@router.delete("/{knowledge_id}")
def delete_knowledge(
    knowledge_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    knowledge_service.delete_knowledge(db, user, knowledge_id)
    db.commit()
    return {"ok": True}
