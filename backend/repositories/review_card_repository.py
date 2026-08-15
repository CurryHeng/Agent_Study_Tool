"""FSRS 复习卡数据访问层。"""
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from models import ReviewCard


def get_by_question_user(db: Session, question_id: int, user_id: int) -> ReviewCard | None:
    return db.get(ReviewCard, (question_id, user_id))


def list_by_questions(db: Session, question_ids: list[int], user_id: int) -> list[ReviewCard]:
    """批量取某用户对一批题目的复习卡（避免 N+1）。"""
    if not question_ids:
        return []
    return (
        db.query(ReviewCard)
        .filter(ReviewCard.user_id == user_id, ReviewCard.question_id.in_(question_ids))
        .all()
    )


def create(db: Session, question_id: int, user_id: int) -> ReviewCard:
    card = ReviewCard(
        question_id=question_id,
        user_id=user_id,
        due=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(card)
    db.flush()
    return card


def get_or_create(db: Session, question_id: int, user_id: int) -> ReviewCard:
    card = get_by_question_user(db, question_id, user_id)
    return card if card is not None else create(db, question_id, user_id)
