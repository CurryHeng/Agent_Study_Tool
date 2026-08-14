"""练习册路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.mindmap import MindMapOut
from schemas.workbook import WorkbookCreate, WorkbookOut, WorkbookUpdate
from services import mindmap_service, workbook_service

router = APIRouter(prefix="/api/workbooks", tags=["workbooks"])


@router.get("", response_model=list[WorkbookOut])
def list_workbooks(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list:
    return workbook_service.list_workbooks(db, user)


@router.post("", status_code=201, response_model=WorkbookOut)
def create_workbook(
    body: WorkbookCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workbook = workbook_service.create_workbook(db, user, body.name, body.description)
    db.commit()
    return workbook


@router.get("/{workbook_id}", response_model=WorkbookOut)
def get_workbook(
    workbook_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return workbook_service.get_workbook(db, user, workbook_id)


@router.put("/{workbook_id}", response_model=WorkbookOut)
def update_workbook(
    workbook_id: int,
    body: WorkbookUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workbook = workbook_service.update_workbook(db, user, workbook_id, body.name, body.description)
    db.commit()
    return workbook


@router.delete("/{workbook_id}")
def delete_workbook(
    workbook_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    workbook_service.delete_workbook(db, user, workbook_id)
    db.commit()
    return {"ok": True}


@router.get("/{workbook_id}/mindmap", response_model=MindMapOut)
def get_mindmap(
    workbook_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workbook = workbook_service.get_workbook(db, user, workbook_id)
    return mindmap_service.build_mindmap(db, workbook)
