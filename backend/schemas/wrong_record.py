"""错题本 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel


class WrongRecordOut(BaseModel):
    id: int
    question_id: int
    wrong_answer: str | None
    wrong_reason: str | None
    reason_type: str | None = None
    explanation: str | None = None
    suggestion: str | None = None
    created_at: datetime
    question_content: str
    correct_answer: str
    question_type: str
    knowledge_id: int | None = None
    knowledge_name: str | None = None


class WrongRecordPageOut(BaseModel):
    """分页信封（with_total=true 时返回），供前端精确计算总页数。"""

    total: int
    items: list[WrongRecordOut]


class WrongRecordUpdate(BaseModel):
    wrong_answer: str | None = None
    wrong_reason: str | None = None


class WrongReasonAnalysis(BaseModel):
    reason_type: str
    explanation: str
    suggestion: str
