"""Chroma 向量库封装（vector store 层）。"""
import chromadb

COLLECTION_NAME = "studyforge"


class VectorStore:
    """对 Chroma collection 的薄封装，供 RAG service 调用。"""

    def __init__(self, path: str, collection_name: str = COLLECTION_NAME):
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        self._collection.upsert(
            ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
        )

    def query(
        self, query_embedding: list[float], top_k: int, where: dict
    ) -> dict:
        return self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    def delete(self, where: dict) -> None:
        self._collection.delete(where=where)
