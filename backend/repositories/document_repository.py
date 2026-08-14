"""文档数据访问层。"""
from sqlalchemy.orm import Session

from models import Document


def create(
    db: Session, workbook_id: int, filename: str, file_type: str, file_path: str
) -> Document:
    doc = Document(
        workbook_id=workbook_id,
        filename=filename,
        file_type=file_type,
        file_path=file_path,
    )
    db.add(doc)
    db.flush()
    return doc


def get_by_id(db: Session, document_id: int) -> Document | None:
    return db.get(Document, document_id)


def list_by_workbook(db: Session, workbook_id: int) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.workbook_id == workbook_id)
        .order_by(Document.id)
        .all()
    )


def delete(db: Session, document: Document) -> None:
    db.delete(document)
    db.flush()
