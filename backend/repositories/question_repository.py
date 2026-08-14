"""题目数据访问层。"""
from sqlalchemy.orm import Session

from models import Question


def list_by_workbooks(db: Session, workbook_ids: list[int]) -> list[Question]:
    """列出多个工作簿下、未删除的题目（含系统内置）。"""
    if not workbook_ids:
        return []
    return (
        db.query(Question)
        .filter(Question.deleted_at.is_(None), Question.workbook_id.in_(workbook_ids))
        .order_by(Question.id)
        .all()
    )


def get_by_id(db: Session, question_id: int) -> Question | None:
    return db.get(Question, question_id)


def get_by_ids(db: Session, question_ids: list[int]) -> list[Question]:
    """批量取题（避免 N+1）。"""
    if not question_ids:
        return []
    return db.query(Question).filter(Question.id.in_(question_ids)).all()


def create(db: Session, **fields) -> Question:
    question = Question(**fields)
    db.add(question)
    db.flush()
    return question


def soft_delete(db: Session, question: Question) -> Question:
    from db.base import utcnow

    question.deleted_at = utcnow()
    db.flush()
    return question
