"""错题本数据访问层。"""
from sqlalchemy.orm import Session

from models import WrongRecord


def get_by_question_user(db: Session, question_id: int, user_id: int) -> WrongRecord | None:
    return (
        db.query(WrongRecord)
        .filter(WrongRecord.question_id == question_id, WrongRecord.user_id == user_id)
        .first()
    )


def get_by_id(db: Session, record_id: int) -> WrongRecord | None:
    return db.get(WrongRecord, record_id)


def update(
    db: Session,
    record: WrongRecord,
    wrong_answer: str | None,
    wrong_reason: str | None,
) -> WrongRecord:
    if wrong_answer is not None:
        record.wrong_answer = wrong_answer
    if wrong_reason is not None:
        record.wrong_reason = wrong_reason
    db.flush()
    return record


def list_by_user(db: Session, user_id: int) -> list[WrongRecord]:
    return (
        db.query(WrongRecord)
        .filter(WrongRecord.user_id == user_id)
        .order_by(WrongRecord.id.desc())
        .all()
    )


def create(
    db: Session, user_id: int, question_id: int, wrong_answer: str | None, wrong_reason: str | None
) -> WrongRecord:
    record = WrongRecord(
        user_id=user_id,
        question_id=question_id,
        wrong_answer=wrong_answer,
        wrong_reason=wrong_reason,
    )
    db.add(record)
    db.flush()
    return record


def record(
    db: Session, user_id: int, question_id: int, wrong_answer: str | None, wrong_reason: str | None
) -> WrongRecord:
    """答错时生成/更新错题本条目（同一用户同一题只保留最新一条）。"""
    existing = get_by_question_user(db, question_id, user_id)
    if existing is None:
        return create(db, user_id, question_id, wrong_answer, wrong_reason)
    existing.wrong_answer = wrong_answer
    if wrong_reason is not None:
        existing.wrong_reason = wrong_reason
    db.flush()
    return existing
