"""刷题业务逻辑：答题 → 判题 → 记录 → FSRS 更新。"""
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from models import User
from models.enums import QuestionType
from repositories import (
    answer_record_repository,
    knowledge_repository,
    question_option_repository,
    question_repository,
    review_card_repository,
    wrong_record_repository,
)
from schemas.question import to_question_out
from schemas.review import AnswerRequest, AnswerResponse, DueItem, ReviewCardOut
from services import access, fsrs_scheduler, grading


def _derive_rating(mode: str, requested: str | None, is_correct: bool | None) -> str:
    if mode == "strict":
        return "good" if is_correct else "again"
    if requested is not None:
        return requested
    if is_correct is None:
        return "good"
    return "good" if is_correct else "again"


def answer_question(
    db: Session, user: User, question_id: int, request: AnswerRequest
) -> AnswerResponse:
    question = access.get_visible_question(db, user, question_id)

    if grading.is_auto_gradable(question.type):
        is_correct = grading.grade_question(question, request.user_answer)
    elif question.type == QuestionType.short_answer:
        # 简答题走 LLM 判分；LLM 不可用时返回 None（降级为用户自评）
        is_correct = grading.grade_short_answer(question, request.user_answer)
    else:
        is_correct = None
    rating = _derive_rating(request.mode, request.rating, is_correct)

    # 1. 答题记录（只增不改）
    answer_record_repository.create(
        db,
        user.id,
        question_id,
        request.user_answer,
        is_correct,
        rating,
        request.mode,
        request.time_spent,
    )

    # 2. 错题本（答错时生成/更新）
    if is_correct is False:
        wrong_record_repository.record(
            db, user.id, question_id, request.user_answer, request.wrong_reason
        )

    # 3. FSRS 复习卡更新
    card = review_card_repository.get_or_create(db, question_id, user.id)
    card.total_attempts += 1
    card.total_correct += 1 if is_correct else 0
    fsrs_scheduler.apply_review(card, rating)

    return AnswerResponse(
        is_correct=is_correct,
        correct_answer=question.answer,
        analysis=question.analysis,
        rating=rating,
        card=ReviewCardOut.model_validate(card),
    )


def get_due(db: Session, user: User, limit: int = 20, favorites: bool = False) -> list[DueItem]:
    """返回到期待复习的题目（favorites=True 时返回收藏的题目）。

    优化：批量取已有复习卡（避免 N+1）；仅为限额内的新题建卡，不一次性为全部题建卡。
    """
    questions = question_repository.list_by_workbooks(db, access.visible_workbook_ids(db, user))
    if not questions:
        return []

    question_ids = [q.id for q in questions]
    existing = review_card_repository.list_by_questions(db, question_ids, user.id)
    card_map = {c.question_id: c for c in existing}

    options = question_option_repository.get_by_question_ids(db, question_ids)
    option_map: dict[int, list] = {}
    for opt in options:
        option_map.setdefault(opt.question_id, []).append(opt)

    knowledge_map: dict[int, str] = {}
    for q in questions:
        if q.knowledge_id is not None and q.knowledge_id not in knowledge_map:
            node = knowledge_repository.get_by_id(db, q.knowledge_id)
            if node is not None:
                knowledge_map[q.knowledge_id] = node.name

    now = datetime.now(UTC).replace(tzinfo=None)
    items: list[tuple] = []  # (question, card)
    new_questions: list = []  # 尚无复习卡的新题
    for q in questions:
        card = card_map.get(q.id)
        if card is None:
            new_questions.append(q)
        elif favorites:
            if card.favorited:
                items.append((q, card))
        elif card.due <= now:
            items.append((q, card))

    # 仅为限额内的新题建卡（favorites 模式下新题无收藏，跳过）
    if not favorites:
        remaining = max(0, limit - len(items))
        for q in new_questions[:remaining]:
            items.append((q, review_card_repository.create(db, q.id, user.id)))

    due = [
        DueItem(
            question=to_question_out(
                q, option_map.get(q.id, []), knowledge_map.get(q.knowledge_id)
            ),
            card=ReviewCardOut.model_validate(card),
        )
        for q, card in items
    ]
    due.sort(key=lambda item: item.card.due)
    return due[:limit]


def toggle_favorite(db: Session, user: User, question_id: int) -> ReviewCardOut:
    """收藏 / 取消收藏，返回更新后的复习卡。"""
    access.get_visible_question(db, user, question_id)
    card = review_card_repository.get_or_create(db, question_id, user.id)
    card.favorited = 1 if not card.favorited else 0
    db.flush()
    return ReviewCardOut.model_validate(card)
