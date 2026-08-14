"""知识点接口测试。"""


def _create(client, headers, workbook, name="第一章", level=0, parent_id=None):
    return client.post(
        "/api/knowledge",
        json={"workbook_id": workbook["id"], "parent_id": parent_id, "name": name, "level": level},
        headers=headers,
    )


def test_create_knowledge(client, auth_headers, workbook):
    resp = _create(client, auth_headers, workbook)
    assert resp.status_code == 201
    assert resp.json()["name"] == "第一章"
    assert resp.json()["level"] == 0


def test_list_knowledge(client, auth_headers, workbook):
    _create(client, auth_headers, workbook)
    resp = client.get(f"/api/knowledge?workbook_id={workbook['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_knowledge(client, auth_headers, workbook):
    node = _create(client, auth_headers, workbook).json()
    resp = client.get(f"/api/knowledge/{node['id']}", headers=auth_headers)
    assert resp.status_code == 200


def test_update_knowledge(client, auth_headers, workbook):
    node = _create(client, auth_headers, workbook).json()
    resp = client.put(f"/api/knowledge/{node['id']}", json={"name": "第二章"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "第二章"


def test_delete_knowledge(client, auth_headers, workbook):
    node = _create(client, auth_headers, workbook).json()
    assert client.delete(f"/api/knowledge/{node['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/knowledge/{node['id']}", headers=auth_headers).status_code == 404


def test_create_in_system_workbook_forbidden(client, auth_headers):
    resp = client.post(
        "/api/knowledge",
        json={"workbook_id": 0, "name": "hack", "level": 0},
        headers=auth_headers,
    )
    assert resp.status_code == 403


def test_list_system_workbook_knowledge_readable(client, auth_headers):
    resp = client.get("/api/knowledge?workbook_id=0", headers=auth_headers)
    assert resp.status_code == 200


def test_knowledge_requires_auth(client):
    assert client.get("/api/knowledge?workbook_id=0").status_code == 401
