"""会话 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationOut(BaseModel):
    id: int
    title: str | None
    created_at: datetime
    updated_at: datetime
    last_message: str | None = None


class ConversationMessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    metadata: dict | None = None
    created_at: datetime
