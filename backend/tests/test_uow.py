"""UoW 事务边界测试（#57）。"""
import pytest

MD_CONTENT = "# 第一章\n\n内容".encode()


@pytest.fixture(autouse=True)
def _isolate_upload_dir(monkeypatch, tmp_path):
    from config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))


def _upload(client, headers, workbook_id):
    return client.post(
        "/api/documents/upload",
        data={"workbook_id": str(workbook_id)},
        files={"file": ("outline.md", MD_CONTENT, "text/markdown")},
        headers=headers,
    )


def test_delete_document_rolls_back_when_vector_cleanup_fails(
    client, auth_headers, workbook, monkeypatch
):
    doc = _upload(client, auth_headers, workbook["id"]).json()

    from services import rag_service

    def boom(document_id):
        raise RuntimeError("Chroma down")

    monkeypatch.setattr(rag_service, "delete_document_vectors", boom)

    with pytest.raises(RuntimeError):
        client.delete(f"/api/documents/{doc['id']}", headers=auth_headers)

    # 数据库文档仍然存在，避免“DB 已删但向量还在”的孤儿
    assert client.get(f"/api/documents/{doc['id']}", headers=auth_headers).status_code == 200


def test_delete_document_success_removes_doc_and_vectors(
    client, auth_headers, workbook, monkeypatch
):
    doc = _upload(client, auth_headers, workbook["id"]).json()
    deleted_ids = []

    from services import rag_service

    def fake_delete(document_id):
        deleted_ids.append(document_id)

    monkeypatch.setattr(rag_service, "delete_document_vectors", fake_delete)

    resp = client.delete(f"/api/documents/{doc['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert deleted_ids == [doc["id"]]
    assert client.get(f"/api/documents/{doc['id']}", headers=auth_headers).status_code == 404
