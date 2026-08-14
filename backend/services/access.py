"""资源访问权限校验。

系统工作簿（id=0）对所有用户只读；其余工作簿/题目/知识点仅属主可读写。
"""
from sqlalchemy.orm import Session

from models import Knowledge, Question, User, Workbook
from repositories import knowledge_repository, question_repository, workbook_repository

SYSTEM_WORKBOOK_ID = 0


class AccessError(Exception):
    """权限/资源异常，携带 HTTP 状态码。"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def get_owned_workbook(db: Session, user: User, workbook_id: int) -> Workbook:
    """获取当前用户拥有的工作簿（可写）。"""
    workbook = workbook_repository.get_by_id(db, workbook_id)
    if workbook is None:
        raise AccessError(404, "练习册不存在")
    if workbook.user_id != user.id:
        raise AccessError(403, "无权操作该练习册")
    return workbook


def get_visible_workbook(db: Session, user: User, workbook_id: int) -> Workbook:
    """获取当前用户可见的工作簿（自己的 + 系统内置）。"""
    workbook = workbook_repository.get_by_id(db, workbook_id)
    if workbook is None:
        raise AccessError(404, "练习册不存在")
    if workbook.id == SYSTEM_WORKBOOK_ID:
        return workbook
    if workbook.user_id != user.id:
        raise AccessError(403, "无权访问该练习册")
    return workbook


def get_owned_question(db: Session, user: User, question_id: int) -> Question:
    question = question_repository.get_by_id(db, question_id)
    if question is None or question.deleted_at is not None:
        raise AccessError(404, "题目不存在")
    workbook = workbook_repository.get_by_id(db, question.workbook_id)
    if workbook is None or workbook.user_id != user.id:
        raise AccessError(403, "无权操作该题目")
    return question


def get_visible_question(db: Session, user: User, question_id: int) -> Question:
    question = question_repository.get_by_id(db, question_id)
    if question is None or question.deleted_at is not None:
        raise AccessError(404, "题目不存在")
    if question.workbook_id == SYSTEM_WORKBOOK_ID:
        return question
    workbook = workbook_repository.get_by_id(db, question.workbook_id)
    if workbook is None or workbook.user_id != user.id:
        raise AccessError(403, "无权访问该题目")
    return question


def get_owned_knowledge(db: Session, user: User, knowledge_id: int) -> Knowledge:
    node = knowledge_repository.get_by_id(db, knowledge_id)
    if node is None:
        raise AccessError(404, "知识点不存在")
    workbook = workbook_repository.get_by_id(db, node.workbook_id)
    if workbook is None or workbook.user_id != user.id:
        raise AccessError(403, "无权操作该知识点")
    return node


def visible_workbook_ids(db: Session, user: User) -> list[int]:
    """当前用户可见的工作簿 ID 列表（系统内置 + 自己的）。"""
    own_ids = [wb.id for wb in workbook_repository.list_by_user(db, user.id)]
    return [SYSTEM_WORKBOOK_ID, *own_ids]
