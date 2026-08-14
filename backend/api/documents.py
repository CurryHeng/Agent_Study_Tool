"""文档路由。"""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.document import DocumentDetailOut, DocumentOut
from services import document_service, rag_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", status_code=201, response_model=DocumentDetailOut)
def upload_document(
    workbook_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = file.file.read()
    out = document_service.upload_document(
        db, user, workbook_id, file.filename or "unnamed", content
    )
    db.commit()
    return out


@router.get("", response_model=list[DocumentOut])
def list_documents(
    workbook_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return document_service.list_documents(db, user, workbook_id)


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return document_service.get_document(db, user, document_id)


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    document_service.delete_document(db, user, document_id)
    rag_service.delete_document_vectors(document_id)
    db.commit()
    return {"ok": True}


@router.post("/{document_id}/index")
def index_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    chunks = rag_service.index_document(db, user, document_id)
    return {"chunks": chunks}
