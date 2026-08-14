"""思维导图（知识树）构建。"""
from sqlalchemy.orm import Session

from models import Workbook
from repositories import knowledge_repository
from schemas.mindmap import MindMapNode, MindMapOut


def build_mindmap(db: Session, workbook: Workbook) -> MindMapOut:
    """把工作簿下的 Knowledge 节点组装成树（根节点 = 工作簿名）。"""
    nodes = knowledge_repository.list_by_workbook(db, workbook.id)
    node_map = {n.id: MindMapNode(id=n.id, label=n.name, children=[]) for n in nodes}
    roots: list[MindMapNode] = []

    for n in nodes:
        if n.parent_id is not None and n.parent_id in node_map:
            node_map[n.parent_id].children.append(node_map[n.id])
        else:
            roots.append(node_map[n.id])

    def sort_rec(node: MindMapNode) -> None:
        node.children.sort(key=lambda c: c.id)
        for c in node.children:
            sort_rec(c)

    for r in roots:
        sort_rec(r)
    roots.sort(key=lambda n: n.id)

    root = MindMapNode(id=workbook.id, label=workbook.name, children=roots)
    return MindMapOut(root=root)


def to_markmap(node: MindMapNode) -> dict:
    """转换为 markmap 渲染所需格式（content + children）。"""
    return {"content": node.label, "children": [to_markmap(c) for c in node.children]}
