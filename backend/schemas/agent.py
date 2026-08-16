"""AI 助手 Pydantic 模型。"""
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentContextEntity(BaseModel):
    type: Literal["knowledge_node", "question", "document", "workbook", "plan"]
    id: int


class AgentChatContext(BaseModel):
    route: str | None = None
    entity: AgentContextEntity | None = None
    extra: dict[str, Any] | None = None


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    workbook_id: int | None = None
    conversation_id: int | None = None
    context: AgentChatContext | None = None


class AgentStep(BaseModel):
    id: int
    tool: str
    status: Literal["success", "failed"]
    args: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    error: str | None = None
    # 兼容旧前端，待所有调用方迁移到 status 后移除。
    ok: bool


class AgentError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class AgentProposal(BaseModel):
    proposal_id: str
    action: str
    target: dict[str, Any]
    changes: dict[str, Any]
    impact: str
    expires_in_sec: int


class AgentChatResponse(BaseModel):
    task_id: str
    status: Literal["completed", "waiting_confirm", "failed", "need_input"]
    conversation_id: int | None = None
    reply: str
    steps: list[AgentStep] = Field(default_factory=list)
    proposals: list[AgentProposal] = Field(default_factory=list)
    navigate: str | None = None
    error: AgentError | None = None
    # 兼容旧 Dashboard，待聊天页完成迁移后移除。
    intent: str
    result: dict


class AgentConfirmRequest(BaseModel):
    proposal_id: str = Field(min_length=1)
    approved: bool


class AgentConfirmResponse(BaseModel):
    ok: bool = True
    result: dict[str, Any] | None = None
