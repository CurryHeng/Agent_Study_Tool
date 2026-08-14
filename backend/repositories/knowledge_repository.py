"""知识点数据访问层。"""
from sqlalchemy.orm import Session

from models import Knowledge


def list_by_workbook(db: Session, workbook_id: int) -> list[Knowledge]:
    return (
        db.query(Knowledge)
        .filter(Knowledge.workbook_id == workbook_id)
        .order_by(Knowledge.level, Knowledge.id)
        .all()
    )


def get_by_id(db: Session, knowledge_id: int) -> Knowledge | None:
    return db.get(Knowledge, knowledge_id)


def get_by_ids(db: Session, knowledge_ids: list[int]) -> list[Knowledge]:
    """批量取知识点（避免 N+1）。"""
    if not knowledge_ids:
        return []
    return db.query(Knowledge).filter(Knowledge.id.in_(knowledge_ids)).all()


def list_by_document(db: Session, document_id: int) -> list[Knowledge]:
    return (
        db.query(Knowledge)
        .filter(Knowledge.source_document_id == document_id)
        .order_by(Knowledge.id)
        .all()
    )


def create(db: Session, **fields) -> Knowledge:
    node = Knowledge(**fields)
    db.add(node)
    db.flush()
    return node


def delete(db: Session, node: Knowledge) -> None:
    db.delete(node)
    db.flush()
