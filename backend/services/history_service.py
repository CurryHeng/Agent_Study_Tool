"""学习活动时间线：聚合上传/出题/答题/错题/复习事件（零新表）。"""
from sqlalchemy.orm import Session

from models import AnswerRecord, Document, Question, ReviewCard, User, WrongRecord
from repositories import question_repository
from schemas.history import HistoryEventOut
from services import access


def _snippet(text: str, limit: int = 40) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def get_history(db: Session, user: User, limit: int = 100) -> list[HistoryEventOut]:
    visible = access.visible_workbook_ids(db, user)

    documents = (
        db.query(Document)
        .filter(Document.workbook_id.in_(visible))
        .order_by(Document.created_at.desc())
        .all()
    )
    questions = (
        db.query(Question)
        .filter(Question.workbook_id.in_(visible), Question.deleted_at.is_(None))
        .order_by(Question.created_at.desc())
        .all()
    )
    answers = (
        db.query(AnswerRecord)
        .filter(AnswerRecord.user_id == user.id)
        .order_by(AnswerRecord.created_at.desc())
        .all()
    )
    wrongs = (
        db.query(WrongRecord)
        .filter(WrongRecord.user_id == user.id)
        .order_by(WrongRecord.created_at.desc())
        .all()
    )
    cards = (
        db.query(ReviewCard)
        .filter(ReviewCard.user_id == user.id)
        .order_by(ReviewCard.updated_at.desc())
        .all()
    )

    qids = {a.question_id for a in answers} | {w.question_id for w in wrongs} | {
        c.question_id for c in cards
    }
    qmap = {q.id: q for q in question_repository.get_by_ids(db, list(qids))}

    events: list[HistoryEventOut] = []

    for d in documents:
        events.append(HistoryEventOut(
            id=f"doc-{d.id}",
            type="upload",
            title="上传文档",
            detail=d.filename,
            created_at=d.created_at,
        ))
    for q in questions:
        events.append(HistoryEventOut(
            id=f"question-{q.id}",
            type="generate",
            title="添加/生成题目",
            detail=_snippet(q.content),
            created_at=q.created_at,
        ))
    for a in answers:
        q = qmap.get(a.question_id)
        events.append(HistoryEventOut(
            id=f"answer-{a.id}",
            type="answer",
            title="答题",
            detail=_snippet(q.content) if q else f"题目 {a.question_id}",
            created_at=a.created_at,
        ))
    for w in wrongs:
        q = qmap.get(w.question_id)
        events.append(HistoryEventOut(
            id=f"wrong-{w.id}",
            type="wrong",
            title="错题记录",
            detail=_snippet(q.content) if q else f"题目 {w.question_id}",
            created_at=w.created_at,
        ))
    for c in cards:
        if c.updated_at:
            q = qmap.get(c.question_id)
            events.append(HistoryEventOut(
                id=f"review-{c.question_id}-{c.user_id}",
                type="review",
                title="复习调度更新",
                detail=_snippet(q.content) if q else f"题目 {c.question_id}",
                created_at=c.updated_at,
            ))

    events.sort(key=lambda e: e.created_at, reverse=True)
    return events[:limit]
