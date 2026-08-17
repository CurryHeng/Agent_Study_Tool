"""知识点 Pydantic 请求/响应模型。"""
from pydantic import BaseModel, ConfigDict, Field


class KnowledgeCreate(BaseModel):
    workbook_id: int
    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    level: int = 0


class KnowledgeUpdate(BaseModel):
    parent_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    level: int | None = None


class KnowledgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workbook_id: int
    parent_id: int | None
    name: str
    description: str | None
    level: int
    source_document_id: int | None


class KnowledgeSuggestion(BaseModel):
    """AI 扩展建议的子知识点（P2-3）。"""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class KnowledgeSuggestOut(BaseModel):
    suggestions: list[KnowledgeSuggestion]
