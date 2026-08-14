"""RAG 业务逻辑：文档索引（chunk→embed→store）与检索。"""
from sqlalchemy.orm import Session

from config import settings
from models import User
from rag import embedding
from rag.chroma import VectorStore
from rag.chunker import chunk_document
from rag.retriever import retrieve as _retrieve
from repositories import document_repository, knowledge_repository
from services import access, document_service


def get_vector_store() -> VectorStore:
    return VectorStore(settings.chroma_path)


def _metadata(workbook_id: int, document_id: int, chunk) -> dict:
    meta = {
        "workbook_id": workbook_id,
        "document_id": document_id,
        "section": chunk.section,
    }
    if chunk.knowledge_id is not None:
        meta["knowledge_id"] = chunk.knowledge_id
    return meta


def index_document(
    db: Session,
    user: User,
    document_id: int,
    embedder=None,
    store: VectorStore | None = None,
) -> int:
    """对已解析文档切块、嵌入并写入 Chroma，返回 chunk 数。"""
    doc = document_repository.get_by_id(db, document_id)
    if doc is None:
        raise access.AccessError(404, "文档不存在")
    access.get_visible_workbook(db, user, doc.workbook_id)

    sections = document_service.read_parsed_sections(document_id)
    nodes = knowledge_repository.list_by_document(db, document_id)
    section_knowledge = [n.id for n in nodes if n.level > 0]  # 跳过文档根节点

    chunks = chunk_document(sections, section_knowledge, document_id, settings.chunk_size)
    if not chunks:
        return 0

    embedder = embedder or embedding.get_embedder()
    store = store or get_vector_store()
    texts = [c.content for c in chunks]
    embeddings = embedder.embed_documents(texts)
    store.upsert(
        ids=[c.chunk_id for c in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[_metadata(doc.workbook_id, document_id, c) for c in chunks],
    )
    return len(chunks)


def retrieve(
    db: Session,
    user: User,
    workbook_id: int,
    query: str,
    knowledge_id: int | None = None,
    top_k: int = 4,
    embedder=None,
    store: VectorStore | None = None,
) -> list[dict]:
    access.get_visible_workbook(db, user, workbook_id)
    embedder = embedder or embedding.get_embedder()
    store = store or get_vector_store()
    return _retrieve(store, embedder, query, workbook_id, knowledge_id, top_k)


def build_context(
    db: Session,
    user: User,
    workbook_id: int,
    knowledge_id: int | None = None,
    top_k: int = 5,
) -> str:
    """构建出题上下文（练习册/知识点名 + RAG 检索片段），检索失败时降级为名称。"""
    workbook = access.get_visible_workbook(db, user, workbook_id)
    parts = [f"练习册：{workbook.name}"]
    query = workbook.name
    if knowledge_id is not None:
        node = knowledge_repository.get_by_id(db, knowledge_id)
        if node is not None:
            parts.append(f"知识点：{node.name}")
            query = node.name
    try:
        chunks = _retrieve(
            get_vector_store(),
            embedding.get_embedder(),
            query,
            workbook_id,
            knowledge_id,
            top_k,
        )
        if chunks:
            parts.append("参考资料：")
            parts.extend(f"- {c['content']}" for c in chunks)
    except Exception:
        pass  # 检索失败时仅用名称上下文
    return "\n".join(parts)


def delete_document_vectors(document_id: int) -> None:
    """删除某文档的所有向量（删除文档时调用，避免孤儿向量）。"""
    try:
        get_vector_store().delete(where={"document_id": document_id})
    except Exception:
        pass  # Chroma 未初始化或无数据时忽略
