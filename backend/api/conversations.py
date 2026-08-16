"""会话列表与消息路由（#46/#47）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.conversation import ConversationCreate, ConversationMessageOut, ConversationOut
from services import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return conversation_service.list_conversations(db, user)


@router.post("", response_model=ConversationOut)
def create_conversation(
    body: ConversationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = conversation_service.create_conversation(db, user, body.title)
    db.commit()
    return conv


@router.get("/{conversation_id}/messages", response_model=list[ConversationMessageOut])
def get_messages(
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return conversation_service.get_messages(db, user, conversation_id, limit, offset)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation_service.delete_conversation(db, user, conversation_id)
    db.commit()
    return {"ok": True}
