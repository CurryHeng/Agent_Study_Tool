"""AI 助手统一入口路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentConfirmRequest,
    AgentConfirmResponse,
)
from services import agent_service, proposal_service

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
def chat(
    body: AgentChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = agent_service.run_task(
        db, user, body.message, body.workbook_id,
        conversation_id=body.conversation_id, context=body.context,
    )
    db.commit()
    return AgentChatResponse(**result)


@router.post("/confirm", response_model=AgentConfirmResponse)
def confirm(
    body: AgentConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = proposal_service.confirm(db, user, body.proposal_id, body.approved)
    db.commit()
    return AgentConfirmResponse(result=result)
