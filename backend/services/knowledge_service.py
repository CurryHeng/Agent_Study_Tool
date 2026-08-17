"""知识点业务逻辑（基础 CRUD + AI 分支建议）。"""
import json

from sqlalchemy.orm import Session

from models import Knowledge, User
from repositories import knowledge_repository
from schemas.knowledge import KnowledgeCreate, KnowledgeSuggestion, KnowledgeUpdate
from services import access


def _validate_parent(
    db: Session,
    workbook_id: int,
    parent_id: int,
    moving_node_id: int | None = None,
) -> Knowledge:
    """校验父节点：存在、同练习册、移动时不构成环。

    moving_node_id 非空时，沿父节点祖先链向上走，遇到被移动节点即构成环
    （把节点移动到自己的后代下会导致导图无限递归）。
    """
    parent = knowledge_repository.get_by_id(db, parent_id)
    if parent is None:
        raise access.AccessError(404, "父知识点不存在")
    if parent.workbook_id != workbook_id:
        raise access.AccessError(400, "父知识点不属于当前练习册")
    if moving_node_id is not None:
        cur: Knowledge | None = parent
        visited: set[int] = set()
        while cur is not None and cur.id not in visited:
            if cur.id == moving_node_id:
                raise access.AccessError(400, "不能把知识点移动到自己的子节点下")
            visited.add(cur.id)
            cur = (
                knowledge_repository.get_by_id(db, cur.parent_id)
                if cur.parent_id is not None
                else None
            )
    return parent


def list_knowledge(
    db: Session, user: User, workbook_id: int,
    page: int | None = None, page_size: int | None = None,
) -> list[Knowledge]:
    access.get_visible_workbook(db, user, workbook_id)
    nodes = knowledge_repository.list_by_workbook(db, workbook_id)
    if page is not None and page_size is not None and page_size > 0:
        start = (page - 1) * page_size
        nodes = nodes[start : start + page_size]
    return nodes


def create_knowledge(db: Session, user: User, data: KnowledgeCreate) -> Knowledge:
    access.get_owned_workbook(db, user, data.workbook_id)
    if data.parent_id is not None:
        _validate_parent(db, data.workbook_id, data.parent_id)
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
        _validate_parent(db, node.workbook_id, data.parent_id, moving_node_id=node.id)
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


# ── P2-3：导图 LLM 分支生成 ────────────────────────────────────────────

SUGGEST_SYSTEM = """你是知识结构规划师。给定一个知识点节点，建议 3-5 个合理的子知识点。
严格只输出 JSON，不要输出解释或多余文本。JSON 格式：
{"suggestions": [{"name": "子知识点名", "description": "一句话说明"}]}
规则：
- name 为 2-30 字的简洁术语
- 子知识点应与父节点主题强相关，是"展开"而非"偏离"
- 禁止与"已有子节点"重名或语义重复"""


def suggest_children(
    db: Session, user: User, knowledge_id: int, llm=None
) -> list[KnowledgeSuggestion]:
    """为知识点节点生成子分支建议（LLM，只读——入库仍需用户确认后走 create）。"""
    from services.llm_service import LLMService

    node = access.get_owned_knowledge(db, user, knowledge_id)
    siblings = knowledge_repository.list_by_workbook(db, node.workbook_id)
    children = [n.name for n in siblings if n.parent_id == node.id]
    # 同级兄弟名作上下文（避免建议与其他分支撞车）
    same_level = [n.name for n in siblings if n.parent_id == node.parent_id and n.id != node.id]

    user_prompt = {
        "节点": node.name,
        "节点描述": node.description or "",
        "已有子节点": children,
        "同级其他节点": same_level[:10],
    }
    llm = llm or LLMService()
    try:
        raw = llm.generate_json(
            SUGGEST_SYSTEM, json.dumps(user_prompt, ensure_ascii=False)
        )
    except Exception as exc:
        if isinstance(exc, access.AccessError):
            raise
        raise access.AccessError(502, f"子分支建议生成失败：{exc}") from exc

    suggestions = raw.get("suggestions") if isinstance(raw, dict) else None
    if not isinstance(suggestions, list):
        raise access.AccessError(502, "子分支建议生成失败：响应格式错误")

    existing = set(children)
    result: list[KnowledgeSuggestion] = []
    for s in suggestions:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name") or "").strip()[:255]
        if not name or name in existing:
            continue
        existing.add(name)
        result.append(
            KnowledgeSuggestion(
                name=name,
                description=str(s["description"])[:500] if s.get("description") else None,
            )
        )
    if not result:
        raise access.AccessError(502, "子分支建议生成失败：未产生有效建议")
    return result


def import_sections(
    db: Session, workbook_id: int, document_id: int, title: str, sections: list
) -> Knowledge:
    """把解析出的章节/知识点写入 Knowledge 树（根节点 = 文档标题）。

    sections 元素需具备 `.title` 与 `.level` 属性（层级越低越靠上）。
    章节标题同样经过垃圾过滤（公式乱码/泛标题不入库）。
    """
    from parsers.text_utils import _clean_kp_name

    root = knowledge_repository.create(
        db,
        workbook_id=workbook_id,
        parent_id=None,
        name=title[:255],
        level=0,
        source_document_id=document_id,
    )
    parents: dict[int, Knowledge] = {0: root}
    for section in sections:
        level = section.level
        parent_levels = [p for p in parents if p < level]
        parent = parents[max(parent_levels)] if parent_levels else root

        clean_title = _clean_kp_name(section.title)
        if clean_title is None:
            # 垃圾章节：正文段落挂到最近的合法父节点下（不丢内容）
            if section.paragraphs:
                extra = "\n".join(section.paragraphs)
                parent.description = (
                    (parent.description or "") + "\n" + extra
                    if parent.description
                    else extra
                )
            continue

        node = knowledge_repository.create(
            db,
            workbook_id=workbook_id,
            parent_id=parent.id,
            name=clean_title[:255],
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

    层级来自章节识别（docs 新数据模型 §4.3：level 0=章 1=节 2=点）——
    章节按标题匹配 import_sections 已建节点，匹配不到则挂到文档根节点；
    知识点直接作为章节子节点（两级：章节→知识点）。
    按 (父节点, 名称) 去重，返回新建节点数。
    """
    from parsers.text_utils import _clean_kp_name

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
            clean = _clean_kp_name(name)
            if clean is None:
                continue
            if any(n.parent_id == chapter_node.id and n.name == clean for n in existing):
                continue
            node = knowledge_repository.create(
                db,
                workbook_id=workbook_id,
                parent_id=chapter_node.id,
                name=clean[:255],
                description=None,
                level=chapter_node.level + 1,
                source_document_id=document_id,
            )
            existing.append(node)
            count += 1
    db.flush()
    return count
