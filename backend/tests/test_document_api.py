"""文档上传 / 知识提取 / 思维导图 接口测试。"""
import pytest

MD_CONTENT = (
    "# 第一章 函数与极限\n\n函数的定义\n\n"
    "## 极限\n\n极限的定义\n\n## 连续\n\n"
    "# 第二章 导数\n\n导数的定义\n"
).encode()


@pytest.fixture(autouse=True)
def _isolate_upload_dir(monkeypatch, tmp_path):
    from config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))


def _upload(client, headers, workbook_id, filename="outline.md", content=MD_CONTENT):
    return client.post(
        "/api/documents/upload",
        data={"workbook_id": str(workbook_id)},
        files={"file": (filename, content, "text/markdown")},
        headers=headers,
    )


def test_upload_extracts_knowledge(client, auth_headers, workbook):
    resp = _upload(client, auth_headers, workbook["id"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "success"
    assert data["file_type"] == "markdown"
    assert len(data["sections"]) == 4

    nodes = client.get(
        f"/api/knowledge?workbook_id={workbook['id']}", headers=auth_headers
    ).json()
    assert len(nodes) == 5  # 根 + 2 章 + 2 知识点
    root = next(n for n in nodes if n["level"] == 0)
    assert root["name"] == "outline"
    assert len([n for n in nodes if n["level"] == 1]) == 2
    assert len([n for n in nodes if n["level"] == 2]) == 2


def test_get_document(client, auth_headers, workbook):
    doc = _upload(client, auth_headers, workbook["id"]).json()
    resp = client.get(f"/api/documents/{doc['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["sections"]) == 4


def test_list_documents(client, auth_headers, workbook):
    _upload(client, auth_headers, workbook["id"])
    resp = client.get(f"/api/documents?workbook_id={workbook['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_delete_document(client, auth_headers, workbook):
    doc = _upload(client, auth_headers, workbook["id"]).json()
    assert client.delete(f"/api/documents/{doc['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/documents/{doc['id']}", headers=auth_headers).status_code == 404


def test_mindmap_tree(client, auth_headers, workbook):
    _upload(client, auth_headers, workbook["id"])
    resp = client.get(f"/api/workbooks/{workbook['id']}/mindmap", headers=auth_headers)
    assert resp.status_code == 200
    root = resp.json()["root"]
    assert root["label"] == workbook["name"]
    assert len(root["children"]) == 1  # 文档根节点
    doc_root = root["children"][0]
    assert doc_root["label"] == "outline"
    assert len(doc_root["children"]) == 2  # 两章


def test_upload_unsupported_type(client, auth_headers, workbook):
    resp = client.post(
        "/api/documents/upload",
        data={"workbook_id": str(workbook["id"])},
        files={"file": ("x.xyz", b"content", "application/octet-stream")},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_upload_image_not_implemented(client, auth_headers, workbook):
    resp = client.post(
        "/api/documents/upload",
        data={"workbook_id": str(workbook["id"])},
        files={"file": ("x.png", b"\x89PNGfake", "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 501


def test_upload_to_system_workbook_forbidden(client, auth_headers):
    resp = client.post(
        "/api/documents/upload",
        data={"workbook_id": "0"},
        files={"file": ("x.md", MD_CONTENT, "text/markdown")},
        headers=auth_headers,
    )
    assert resp.status_code == 403
