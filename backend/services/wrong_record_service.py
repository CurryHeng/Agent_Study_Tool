"""错题本业务逻辑（列出/编辑错题，附带题干、正确答案与知识点）。"""
from sqlalchemy.orm import Session

from models import Knowledge, Question, User
from repositories import knowledge_repository, question_repository, wrong_record_repository
from schemas.wrong_record import WrongRecordOut
from services import access


def _to_out(r, question: Question | None, knowledge: Knowledge | None) -> WrongRecordOut:
    return WrongRecordOut(
        id=r.id,
        question_id=r.question_id,
        wrong_answer=r.wrong_answer,
        wrong_reason=r.wrong_reason,
        created_at=r.created_at,
        question_content=question.content if question else "",
        correct_answer=question.answer if question else "",
        question_type=question.type.value if question else "",
        knowledge_id=question.knowledge_id if question else None,
        knowledge_name=knowledge.name if knowledge else None,
    )


def _fetch_knowledge(db: Session, question: Question | None) -> Knowledge | None:
    if question is None or question.knowledge_id is None:
        return None
    return knowledge_repository.get_by_id(db, question.knowledge_id)


def list_wrong_records(
    db: Session, user: User, knowledge_id: int | None = None
) -> list[WrongRecordOut]:
    records = wrong_record_repository.list_by_user(db, user.id)
    if not records:
        return []
    # 批量取题目与知识点，避免逐条 N+1 查询；排除已软删的题目（错题本不显示）
    questions = {
        q.id: q
        for q in question_repository.get_by_ids(db, [r.question_id for r in records])
        if q.deleted_at is None
    }
    if knowledge_id is not None:
        questions = {
            qid: q for qid, q in questions.items() if q.knowledge_id == knowledge_id
        }
    knowledge_ids = [q.knowledge_id for q in questions.values() if q.knowledge_id is not None]
    knowledge_map = {k.id: k for k in knowledge_repository.get_by_ids(db, knowledge_ids)}
    result: list[WrongRecordOut] = []
    for r in records:
        question = questions.get(r.question_id)
        if question is None:
            continue
        result.append(_to_out(r, question, knowledge_map.get(question.knowledge_id)))
    return result


def update_wrong_record(
    db: Session,
    user: User,
    record_id: int,
    fields: dict,
) -> WrongRecordOut:
    record = wrong_record_repository.get_by_id(db, record_id)
    if record is None:
        raise access.AccessError(404, "错题记录不存在")
    if record.user_id != user.id:
        raise access.AccessError(403, "无权操作该错题记录")
    record = wrong_record_repository.update(db, record, fields)
    question = question_repository.get_by_id(db, record.question_id)
    return _to_out(record, question, _fetch_knowledge(db, question))
