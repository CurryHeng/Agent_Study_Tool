"""AI 助手 Pydantic 模型。"""
from typing import Any

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    workbook_id: int | None = None


class AgentProposal(BaseModel):
    proposal_id: str
    action: str
    target: dict[str, Any]
    changes: dict[str, Any]
    impact: str
    expires_in_sec: int


class AgentChatResponse(BaseModel):
    task_id: str
    conversation_id: int | None = None
    reply: str
    steps: list[dict] = Field(default_factory=list)
    proposals: list[AgentProposal] = Field(default_factory=list)
    navigate: str | None = None
    # 兼容旧 Dashboard，待聊天页完成迁移后移除。
    intent: str
    result: dict


class AgentConfirmRequest(BaseModel):
    proposal_id: str = Field(min_length=1)
    approved: bool


class AgentConfirmResponse(BaseModel):
    ok: bool = True
    result: dict[str, Any] | None = None
