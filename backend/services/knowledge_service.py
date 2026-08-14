"""知识点业务逻辑（基础 CRUD）。"""
from sqlalchemy.orm import Session

from models import Knowledge, User
from repositories import knowledge_repository
from schemas.knowledge import KnowledgeCreate, KnowledgeUpdate
from services import access


def list_knowledge(db: Session, user: User, workbook_id: int) -> list[Knowledge]:
    access.get_visible_workbook(db, user, workbook_id)
    return knowledge_repository.list_by_workbook(db, workbook_id)


def create_knowledge(db: Session, user: User, data: KnowledgeCreate) -> Knowledge:
    access.get_owned_workbook(db, user, data.workbook_id)
    return knowledge_repository.create(
        db,
        workbook_id=data.workbook_id,
        parent_id=data.parent_id,
        name=data.name,
        description=data.description,
        level=data.level,
    )


def get_knowledge(db: Session, user: User, knowledge_id: int) -> Knowledge:
    node = knowledge_repository.get_by_id(db, knowledge_id)
    if node is None:
        raise access.AccessError(404, "知识点不存在")
    access.get_visible_workbook(db, user, node.workbook_id)
    return node


def update_knowledge(
    db: Session, user: User, knowledge_id: int, data: KnowledgeUpdate
) -> Knowledge:
    node = access.get_owned_knowledge(db, user, knowledge_id)
    if data.parent_id is not None:
        node.parent_id = data.parent_id
    if data.name is not None:
        node.name = data.name
    if data.description is not None:
        node.description = data.description
    if data.level is not None:
        node.level = data.level
    db.flush()
    return node


def delete_knowledge(db: Session, user: User, knowledge_id: int) -> None:
    node = access.get_owned_knowledge(db, user, knowledge_id)
    knowledge_repository.delete(db, node)


def import_sections(
    db: Session, workbook_id: int, document_id: int, title: str, sections: list
) -> Knowledge:
    """把解析出的章节/知识点写入 Knowledge 树（根节点 = 文档标题）。

    sections 元素需具备 `.title` 与 `.level` 属性（层级越低越靠上）。
    """
    root = knowledge_repository.create(
        db,
        workbook_id=workbook_id,
        parent_id=None,
        name=title,
        level=0,
        source_document_id=document_id,
    )
    parents: dict[int, Knowledge] = {0: root}
    for section in sections:
        level = section.level
        parent = parents[max(p for p in parents if p < level)]
        node = knowledge_repository.create(
            db,
            workbook_id=workbook_id,
            parent_id=parent.id,
            name=section.title,
            level=level,
            source_document_id=document_id,
        )
        parents[level] = node
        for deeper in [p for p in parents if p > level]:
            del parents[deeper]
    return root


def import_knowledge_points(
    db: Session, workbook_id: int, document_id: int, root: Knowledge, knowledge: dict
) -> int:
    """把导入 Agent 提取的知识点挂到文档知识树（在 import_sections 之后调用）。

    章节按标题匹配 import_sections 已建节点，匹配不到则挂到文档根节点；
    知识点作为章节的子节点（description 存释义，importance/difficulty 不入库——
    Knowledge 表无这两列）。按 (父节点, 名称) 去重，返回新建知识点数。
    """
    chapters = knowledge.get("chapters") or []
    existing = knowledge_repository.list_by_document(db, document_id)
    by_name = {n.name: n for n in existing}
    count = 0
    for ch in chapters:
        chapter_node = by_name.get(ch.get("title")) or root
        # 章节的"术语：释义"汇总写入章节描述
        if ch.get("content") and not chapter_node.description:
            chapter_node.description = ch["content"]
        for kp in ch.get("knowledge_points") or []:
            name = str(kp.get("name") or "").strip()
            if not name:
                continue
            if any(n.parent_id == chapter_node.id and n.name == name for n in existing):
                continue
            node = knowledge_repository.create(
                db,
                workbook_id=workbook_id,
                parent_id=chapter_node.id,
                name=name[:255],
                description=None,
                level=chapter_node.level + 1,
                source_document_id=document_id,
            )
            existing.append(node)
            count += 1
    db.flush()
    return count
