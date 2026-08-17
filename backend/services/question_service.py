"""题目业务逻辑（CRUD + 软删除 + 选项管理）。"""
from sqlalchemy.orm import Session

from models import User
from models.enums import CHOICE_TYPES, QuestionSource, QuestionStatus
from repositories import (
    knowledge_repository,
    question_option_repository,
    question_repository,
)
from schemas.question import QuestionCreate, QuestionOut, QuestionUpdate, to_question_out
from services import access


def _validate_question(type_, options: list) -> None:
    """校验题型与选项一致性（选择题必须带选项，非选择题不带选项）。"""
    if type_ in CHOICE_TYPES and len(options) < 2:
        raise access.AccessError(422, "选择题至少需要 2 个选项")
    if type_ not in CHOICE_TYPES and len(options) > 0:
        raise access.AccessError(422, "非选择题不应携带选项")


def _validate_knowledge(db: Session, workbook_id: int, knowledge_id: int | None) -> None:
    if knowledge_id is None:
        return
    node = knowledge_repository.get_by_id(db, knowledge_id)
    if node is None:
        raise access.AccessError(422, "知识点不存在")
    if node.workbook_id != workbook_id:
        raise access.AccessError(422, "知识点不属于该练习册")


def _knowledge_name(db: Session, question) -> str | None:
    if question.knowledge_id is None:
        return None
    node = knowledge_repository.get_by_id(db, question.knowledge_id)
    return node.name if node else None


def list_questions(
    db: Session, user: User, workbook_id: int | None = None,
    page: int | None = None, page_size: int | None = None,
    with_total: bool = False,
) -> list[QuestionOut] | dict:
    visible_ids = access.visible_workbook_ids(db, user)
    if workbook_id is not None:
        if workbook_id not in visible_ids:
            raise access.AccessError(403, "无权访问该练习册")
        workbook_ids = [workbook_id]
    else:
        workbook_ids = visible_ids

    questions = question_repository.list_by_workbooks(db, workbook_ids)
    options = question_option_repository.get_by_question_ids(
        db, [q.id for q in questions]
    )
    option_map: dict[int, list] = {}
    for opt in options:
        option_map.setdefault(opt.question_id, []).append(opt)
    # 批量回填知识点名称（与 /review/due、/wrong-records 行为一致）
    knowledge_ids = [q.knowledge_id for q in questions if q.knowledge_id is not None]
    knowledge_map = {k.id: k for k in knowledge_repository.get_by_ids(db, knowledge_ids)}
    result = [
        to_question_out(
            q,
            option_map.get(q.id, []),
            knowledge_map[q.knowledge_id].name
            if q.knowledge_id in knowledge_map
            else None,
        )
        for q in questions
    ]
    total = len(result)
    if page is not None and page_size is not None and page_size > 0:
        start = (page - 1) * page_size
        result = result[start : start + page_size]
    if with_total:
        return {"total": total, "items": result}
    return result


def create_question(db: Session, user: User, data: QuestionCreate) -> QuestionOut:
    access.get_owned_workbook(db, user, data.workbook_id)
    _validate_question(data.type, data.options)
    _validate_knowledge(db, data.workbook_id, data.knowledge_id)

    question = question_repository.create(
        db,
        workbook_id=data.workbook_id,
        knowledge_id=data.knowledge_id,
        type=data.type,
        content=data.content,
        answer=data.answer,
        analysis=data.analysis,
        summary=data.summary,
        image=data.image,
        difficulty=data.difficulty,
        source=QuestionSource.user,
        status=QuestionStatus.approved,
        original_number=data.original_number,
        question_number=data.question_number,
    )
    if data.options:
        question_option_repository.replace(db, question.id, data.options)
    options = question_option_repository.get_by_question_ids(db, [question.id])
    return to_question_out(question, options, _knowledge_name(db, question))


def get_question(db: Session, user: User, question_id: int) -> QuestionOut:
    question = access.get_visible_question(db, user, question_id)
    options = question_option_repository.get_by_question_ids(db, [question.id])
    return to_question_out(question, options, _knowledge_name(db, question))


def update_question(db: Session, user: User, question_id: int, data: QuestionUpdate) -> QuestionOut:
    question = access.get_owned_question(db, user, question_id)

    final_type = data.type if data.type is not None else question.type
    existing_options = question_option_repository.get_by_question_ids(db, [question.id])
    options_changed = data.options is not None
    final_options = data.options if options_changed else existing_options
    _validate_question(final_type, final_options)

    if data.knowledge_id is not None:
        _validate_knowledge(db, question.workbook_id, data.knowledge_id)
        question.knowledge_id = data.knowledge_id

    if data.type is not None:
        question.type = data.type
    if data.content is not None:
        question.content = data.content
    if data.answer is not None:
        question.answer = data.answer
    if data.analysis is not None:
        question.analysis = data.analysis
    if data.summary is not None:
        question.summary = data.summary
    if data.image is not None:
        question.image = data.image
    if data.difficulty is not None:
        question.difficulty = data.difficulty
    if data.original_number is not None:
        question.original_number = data.original_number
    if data.question_number is not None:
        question.question_number = data.question_number

    db.flush()
    if options_changed:
        question_option_repository.replace(db, question.id, final_options)
        final_options = question_option_repository.get_by_question_ids(db, [question.id])
    return to_question_out(question, final_options, _knowledge_name(db, question))


def delete_question(db: Session, user: User, question_id: int) -> None:
    question = access.get_owned_question(db, user, question_id)
    question_repository.soft_delete(db, question)
