"""答题记录数据访问层（只增不改的审计日志）。"""
from sqlalchemy.orm import Session

from models import AnswerRecord


def create(
    db: Session,
    user_id: int,
    question_id: int,
    user_answer: str | None,
    is_correct: bool | None,
    rating: str,
    mode: str,
    time_spent: int | None,
) -> AnswerRecord:
    is_correct_int = None if is_correct is None else (1 if is_correct else 0)
    record = AnswerRecord(
        user_id=user_id,
        question_id=question_id,
        user_answer=user_answer,
        is_correct=is_correct_int,
        rating=rating,
        mode=mode,
        time_spent=time_spent,
    )
    db.add(record)
    db.flush()
    return record
