"""RAG 集成测试（用假 embedding + 临时 Chroma 目录，避免下载模型）。"""
import hashlib

import pytest

from rag.chroma import VectorStore
from services import rag_service

MD_A = "# 第一章\n\n函数\n\n# 第二章\n\n导数\n".encode()
MD_B = "# 第一章\n\n财务报表\n\n# 第二章\n\n资本成本\n".encode()


class FakeEmbedder:
    """确定性假 embedding（哈希到固定维度），仅用于测试链路与隔离。"""

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]

    def embed_query(self, text):
        return self._embed(text)

    def _embed(self, text):
        dim = 32
        vec = [0.0] * dim
        for ch in text:
            h = hashlib.md5(ch.encode()).digest()
            vec[int.from_bytes(h[:1], "big") % dim] += 1.0
        norm = (sum(v * v for v in vec) ** 0.5) or 1.0
        return [v / norm for v in vec]


@pytest.fixture(autouse=True)
def _isolate_upload(monkeypatch, tmp_path):
    from config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))


def _upload(client, headers, workbook_id, filename, content):
    return client.post(
        "/api/documents/upload",
        data={"workbook_id": str(workbook_id)},
        files={"file": (filename, content, "text/markdown")},
        headers=headers,
    )


def test_index_and_retrieve_isolation(client, auth_headers, registered_user, session, tmp_path):
    from models import User

    user = session.get(User, registered_user["user"]["id"])
    wb_a = client.post("/api/workbooks", json={"name": "A"}, headers=auth_headers).json()
    wb_b = client.post("/api/workbooks", json={"name": "B"}, headers=auth_headers).json()
    doc_a = _upload(client, auth_headers, wb_a["id"], "a.md", MD_A).json()
    doc_b = _upload(client, auth_headers, wb_b["id"], "b.md", MD_B).json()

    store = VectorStore(str(tmp_path / "chroma"))
    embedder = FakeEmbedder()
    n_a = rag_service.index_document(session, user, doc_a["id"], embedder=embedder, store=store)
    n_b = rag_service.index_document(session, user, doc_b["id"], embedder=embedder, store=store)
    assert n_a == 2
    assert n_b == 2

    results = rag_service.retrieve(
        session, user, wb_a["id"], "函数", embedder=embedder, store=store
    )
    assert len(results) >= 1
    assert all(r["metadata"]["workbook_id"] == wb_a["id"] for r in results)


def test_retrieve_knowledge_filter(client, auth_headers, registered_user, session, tmp_path):
    from models import User

    user = session.get(User, registered_user["user"]["id"])
    wb = client.post("/api/workbooks", json={"name": "A"}, headers=auth_headers).json()
    doc = _upload(client, auth_headers, wb["id"], "a.md", MD_A).json()
    nodes = client.get(f"/api/knowledge?workbook_id={wb['id']}", headers=auth_headers).json()
    chapter = next(n for n in nodes if n["level"] == 1)

    store = VectorStore(str(tmp_path / "chroma"))
    embedder = FakeEmbedder()
    rag_service.index_document(session, user, doc["id"], embedder=embedder, store=store)

    results = rag_service.retrieve(
        session,
        user,
        wb["id"],
        "函数",
        knowledge_id=chapter["id"],
        embedder=embedder,
        store=store,
    )
    assert len(results) >= 1
    assert all(r["metadata"]["knowledge_id"] == chapter["id"] for r in results)


def test_rag_api_endpoints(client, auth_headers, monkeypatch, tmp_path):
    from config import settings
    from rag import embedding

    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "chroma"))
    monkeypatch.setattr(embedding, "get_embedder", lambda: FakeEmbedder())

    wb = client.post("/api/workbooks", json={"name": "A"}, headers=auth_headers).json()
    doc = _upload(client, auth_headers, wb["id"], "a.md", MD_A).json()

    resp = client.post(f"/api/documents/{doc['id']}/index", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["chunks"] == 2

    resp2 = client.post(
        "/api/rag/retrieve",
        json={"workbook_id": wb["id"], "query": "函数"},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    items = resp2.json()
    assert len(items) >= 1
    assert all(i["metadata"]["workbook_id"] == wb["id"] for i in items)
