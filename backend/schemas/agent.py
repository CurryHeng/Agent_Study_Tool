"""AI 助手 Pydantic 模型。"""
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    workbook_id: int | None = None


class AgentChatResponse(BaseModel):
    task_id: str
    conversation_id: int | None = None
    reply: str
    steps: list[dict] = []
    proposals: list[dict] = []
    navigate: str | None = None
    # 兼容旧 Dashboard，待聊天页完成迁移后移除。
    intent: str
    result: dict
