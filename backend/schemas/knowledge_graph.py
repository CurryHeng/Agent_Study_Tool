"""知识图谱 Pydantic 模型。"""
from pydantic import BaseModel


class KnowledgeGraphNode(BaseModel):
    id: int
    name: str
    parent_id: int | None = None
    level: int


class KnowledgeGraphEdge(BaseModel):
    source: int
    target: int
    type: str
    label: str | None = None


class KnowledgeGraphOut(BaseModel):
    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]
