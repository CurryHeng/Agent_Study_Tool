"""出题 / 审核的 Pydantic 模型。"""
from pydantic import BaseModel, Field

from models.enums import QuestionType


class GeneratedOption(BaseModel):
    option_key: str = Field(min_length=1, max_length=8)
    content: str = Field(min_length=1)
    sort_order: int = 0


class GeneratedQuestion(BaseModel):
    type: QuestionType
    content: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    analysis: str | None = None
    difficulty: int = Field(default=1, ge=1, le=5)
    options: list[GeneratedOption] = []


class GenerationOutput(BaseModel):
    questions: list[GeneratedQuestion]


class ReviewResult(BaseModel):
    passed: bool
    score: float = 0.0
    issues: list[str] = []


class GenerateRequest(BaseModel):
    workbook_id: int
    knowledge_id: int | None = None
    type: QuestionType = QuestionType.single_choice
    count: int = Field(default=5, ge=1, le=20)
    difficulty: int = Field(default=1, ge=1, le=5)
