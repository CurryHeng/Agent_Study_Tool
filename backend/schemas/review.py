"""刷题 / 答题 Pydantic 模型。"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from schemas.question import QuestionOut

ReviewMode = Literal["relaxed", "normal", "strict"]
ReviewRating = Literal["again", "hard", "good", "easy"]


class AnswerRequest(BaseModel):
    user_answer: str | None = None
    mode: ReviewMode = "relaxed"
    rating: ReviewRating | None = None
    time_spent: int | None = None
    wrong_reason: str | None = None


class ReviewCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: int
    # FSRS-6 调度状态
    state: str
    step: int | None
    stability: float | None
    difficulty: float | None
    due: datetime
    last_review: datetime | None
    # 业务统计
    total_attempts: int
    total_correct: int
    favorited: int


class AnswerResponse(BaseModel):
    is_correct: bool | None
    correct_answer: str
    analysis: str | None
    rating: str
    card: ReviewCardOut


class DueItem(BaseModel):
    question: QuestionOut
    card: ReviewCardOut
