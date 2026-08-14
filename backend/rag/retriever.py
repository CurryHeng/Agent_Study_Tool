"""检索接口（query → embedding → similarity search → metadata filter → top-k）。"""
from rag.chroma import VectorStore
from rag.embedding import BaseEmbedder


def retrieve(
    store: VectorStore,
    embedder: BaseEmbedder,
    query: str,
    workbook_id: int,
    knowledge_id: int | None = None,
    top_k: int = 4,
) -> list[dict]:
    """按 workbook 隔离检索；可选按 knowledge_id 进一步过滤。"""
    query_embedding = embedder.embed_query(query)
    where: dict = {"workbook_id": workbook_id}
    if knowledge_id is not None:
        where = {
            "$and": [
                {"workbook_id": workbook_id},
                {"knowledge_id": knowledge_id},
            ]
        }

    raw = store.query(query_embedding, top_k, where)
    ids = raw.get("ids", [[]])[0]
    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    results = []
    for i in range(len(ids)):
        results.append(
            {
                "chunk_id": ids[i],
                "content": documents[i],
                "metadata": metadatas[i],
                "distance": distances[i],
            }
        )
    return results
