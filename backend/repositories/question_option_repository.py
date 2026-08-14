"""题目选项数据访问层。"""
from sqlalchemy.orm import Session

from models import QuestionOption


def get_by_question_ids(db: Session, question_ids: list[int]) -> list[QuestionOption]:
    """批量取多个题目的选项（按 sort_order 排序）。"""
    if not question_ids:
        return []
    return (
        db.query(QuestionOption)
        .filter(QuestionOption.question_id.in_(question_ids))
        .order_by(QuestionOption.question_id, QuestionOption.sort_order)
        .all()
    )


def replace(db: Session, question_id: int, options: list) -> None:
    """整体替换某题的选项：先删后插。"""
    db.query(QuestionOption).filter(QuestionOption.question_id == question_id).delete()
    for opt in options:
        db.add(
            QuestionOption(
                question_id=question_id,
                option_key=opt.option_key,
                content=opt.content,
                sort_order=opt.sort_order,
            )
        )
    db.flush()
