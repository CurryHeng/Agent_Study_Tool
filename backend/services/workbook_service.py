"""练习册业务逻辑。"""
from sqlalchemy.orm import Session

from models import AnswerRecord, Question, User, Workbook, WrongRecord
from repositories import workbook_repository
from services import access


def list_workbooks(db: Session, user: User) -> list[Workbook]:
    return workbook_repository.list_by_user(db, user.id)


def create_workbook(db: Session, user: User, name: str, description: str | None) -> Workbook:
    return workbook_repository.create(db, user.id, name, description)


def get_workbook(db: Session, user: User, workbook_id: int) -> Workbook:
    return access.get_visible_workbook(db, user, workbook_id)


def update_workbook(
    db: Session, user: User, workbook_id: int, name: str | None, description: str | None
) -> Workbook:
    workbook = access.get_owned_workbook(db, user, workbook_id)
    return workbook_repository.update(db, workbook, name, description)


def delete_workbook(db: Session, user: User, workbook_id: int) -> None:
    workbook = access.get_owned_workbook(db, user, workbook_id)
    # answer_records / wrong_records 对 question 为 RESTRICT（防静默丢失），
    # 用户显式删除练习册时需先显式清理这些学习记录，否则级联删题会触发外键约束失败。
    question_ids = db.query(Question.id).filter(Question.workbook_id == workbook.id)
    db.query(WrongRecord).filter(WrongRecord.question_id.in_(question_ids)).delete(
        synchronize_session=False
    )
    db.query(AnswerRecord).filter(AnswerRecord.question_id.in_(question_ids)).delete(
        synchronize_session=False
    )
    workbook_repository.delete(db, workbook)
