"""文档 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.enums import DocumentStatus
from schemas.generation import GeneratedQuestion


class SectionOut(BaseModel):
    title: str
    level: int
    paragraphs: list[str] = []


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workbook_id: int
    filename: str
    file_type: str
    file_path: str
    file_size: int = 0
    status: DocumentStatus
    created_at: datetime


class DocumentDetailOut(DocumentOut):
    sections: list[SectionOut] = []
    generated_questions: list[GeneratedQuestion] | None = None
