"""RAG 检索 Pydantic 模型。"""
from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    workbook_id: int
    query: str = Field(min_length=1)
    knowledge_id: int | None = None
    top_k: int = Field(default=4, ge=1, le=20)


class RetrievalItem(BaseModel):
    chunk_id: str
    content: str
    metadata: dict
    distance: float
