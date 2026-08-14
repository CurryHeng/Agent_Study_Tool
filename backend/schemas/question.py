"""题目与选项 Pydantic 请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.enums import QuestionSource, QuestionStatus, QuestionType
from models.question import Question
from models.question_option import QuestionOption


class QuestionOptionIn(BaseModel):
    option_key: str = Field(min_length=1, max_length=8)
    content: str = Field(min_length=1)
    sort_order: int = 0


class QuestionOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    option_key: str
    content: str
    sort_order: int


class QuestionCreate(BaseModel):
    workbook_id: int
    knowledge_id: int | None = None
    type: QuestionType
    content: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    analysis: str | None = None
    summary: str | None = None
    image: str | None = None
    difficulty: int = Field(default=1, ge=1, le=5)
    options: list[QuestionOptionIn] = []
    original_number: str | None = None
    question_number: str | None = None


class QuestionUpdate(BaseModel):
    knowledge_id: int | None = None
    type: QuestionType | None = None
    content: str | None = Field(default=None, min_length=1)
    answer: str | None = Field(default=None, min_length=1)
    analysis: str | None = None
    summary: str | None = None
    image: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    options: list[QuestionOptionIn] | None = None
    original_number: str | None = None
    question_number: str | None = None


class QuestionOut(BaseModel):
    id: int
    workbook_id: int
    knowledge_id: int | None
    type: QuestionType
    content: str
    answer: str
    analysis: str | None
    summary: str | None
    image: str | None
    difficulty: int
    source: QuestionSource
    status: QuestionStatus
    original_number: str | None
    question_number: str | None
    created_at: datetime
    updated_at: datetime
    options: list[QuestionOptionOut]
    knowledge_name: str | None = None


def to_question_out(
    question: Question,
    options: list[QuestionOption],
    knowledge_name: str | None = None,
) -> QuestionOut:
    """把 ORM 对象 + 选项列表组装成响应模型。"""
    return QuestionOut(
        id=question.id,
        workbook_id=question.workbook_id,
        knowledge_id=question.knowledge_id,
        type=question.type,
        content=question.content,
        answer=question.answer,
        analysis=question.analysis,
        summary=question.summary,
        image=question.image,
        difficulty=question.difficulty,
        source=question.source,
        status=question.status,
        original_number=question.original_number,
        question_number=question.question_number,
        created_at=question.created_at,
        updated_at=question.updated_at,
        options=[QuestionOptionOut.model_validate(o) for o in options],
        knowledge_name=knowledge_name,
    )
