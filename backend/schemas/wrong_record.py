"""错题本 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel


class WrongRecordOut(BaseModel):
    id: int
    question_id: int
    wrong_answer: str | None
    wrong_reason: str | None
    created_at: datetime
    question_content: str
    correct_answer: str
    question_type: str
    knowledge_name: str | None = None


class WrongRecordUpdate(BaseModel):
    wrong_answer: str | None = None
    wrong_reason: str | None = None
