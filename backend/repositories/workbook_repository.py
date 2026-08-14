"""练习册数据访问层。"""
from sqlalchemy.orm import Session

from models import Workbook


def list_by_user(db: Session, user_id: int) -> list[Workbook]:
    return (
        db.query(Workbook)
        .filter(Workbook.user_id == user_id)
        .order_by(Workbook.id)
        .all()
    )


def get_by_id(db: Session, workbook_id: int) -> Workbook | None:
    return db.get(Workbook, workbook_id)


def create(db: Session, user_id: int, name: str, description: str | None) -> Workbook:
    workbook = Workbook(user_id=user_id, name=name, description=description)
    db.add(workbook)
    db.flush()
    return workbook


def update(db: Session, workbook: Workbook, name: str | None, description: str | None) -> Workbook:
    if name is not None:
        workbook.name = name
    if description is not None:
        workbook.description = description
    db.flush()
    return workbook


def delete(db: Session, workbook: Workbook) -> None:
    db.delete(workbook)
    db.flush()
