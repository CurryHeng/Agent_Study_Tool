"""思维导图（知识树）Pydantic 模型。"""
from pydantic import BaseModel


class MindMapNode(BaseModel):
    id: int
    label: str
    children: list["MindMapNode"] = []


class MindMapOut(BaseModel):
    root: MindMapNode
