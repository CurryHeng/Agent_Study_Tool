"""知识图谱服务：返回知识点节点与边（树边 + 语义关联）。"""
from sqlalchemy.orm import Session

from models import KnowledgeRelation, User
from repositories import knowledge_repository
from schemas.knowledge_graph import KnowledgeGraphEdge, KnowledgeGraphNode, KnowledgeGraphOut
from services import access


def get_knowledge_graph(db: Session, user: User, workbook_id: int) -> KnowledgeGraphOut:
    access.get_visible_workbook(db, user, workbook_id)
    nodes = knowledge_repository.list_by_workbook(db, workbook_id)

    node_out = [
        KnowledgeGraphNode(id=n.id, name=n.name, parent_id=n.parent_id, level=n.level)
        for n in nodes
    ]
    node_ids = {n.id for n in nodes}
    edges: list[KnowledgeGraphEdge] = []

    # 树形父子边
    for n in nodes:
        if n.parent_id is not None and n.parent_id in node_ids:
            edges.append(KnowledgeGraphEdge(source=n.parent_id, target=n.id, type="parent"))

    # 语义关联边
    relations = (
        db.query(KnowledgeRelation)
        .filter(KnowledgeRelation.workbook_id == workbook_id)
        .all()
    )
    for r in relations:
        if r.source_knowledge_id in node_ids and r.target_knowledge_id in node_ids:
            edges.append(KnowledgeGraphEdge(
                source=r.source_knowledge_id,
                target=r.target_knowledge_id,
                type=r.relation_type,
                label=r.note,
            ))

    return KnowledgeGraphOut(nodes=node_out, edges=edges)
