"""AI 助手 Pydantic 模型。"""
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    workbook_id: int | None = None


class AgentChatResponse(BaseModel):
    task_id: str
    intent: str
    result: dict
