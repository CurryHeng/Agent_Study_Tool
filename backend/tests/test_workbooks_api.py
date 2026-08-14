"""练习册接口测试。"""
import uuid


def _create(client, headers, name="练习册A"):
    return client.post(
        "/api/workbooks", json={"name": name, "description": "desc"}, headers=headers
    )


def test_create_workbook(client, auth_headers):
    resp = _create(client, auth_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "练习册A"


def test_list_workbooks(client, auth_headers):
    _create(client, auth_headers)
    resp = client.get("/api/workbooks", headers=auth_headers)
    assert resp.status_code == 200
    names = [w["name"] for w in resp.json()]
    assert "练习册A" in names
    # 用户自己的列表不应包含系统内置工作簿
    assert all(w["id"] != 0 for w in resp.json())


def test_get_workbook(client, auth_headers):
    wb = _create(client, auth_headers).json()
    resp = client.get(f"/api/workbooks/{wb['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "练习册A"


def test_update_workbook(client, auth_headers):
    wb = _create(client, auth_headers).json()
    resp = client.put(f"/api/workbooks/{wb['id']}", json={"name": "新名字"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名字"


def test_delete_workbook(client, auth_headers):
    wb = _create(client, auth_headers).json()
    assert client.delete(f"/api/workbooks/{wb['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/workbooks/{wb['id']}", headers=auth_headers).status_code == 404


def test_delete_studied_workbook(client, auth_headers, workbook):
    """删除已产生答题/错题记录的练习册（回归：RESTRICT 外键曾导致 500）。"""
    q = client.post(
        "/api/questions",
        json={
            "workbook_id": workbook["id"],
            "type": "single_choice",
            "content": "1+1=?",
            "answer": "B",
            "options": [
                {"option_key": "A", "content": "0", "sort_order": 0},
                {"option_key": "B", "content": "2", "sort_order": 1},
            ],
        },
        headers=auth_headers,
    ).json()
    # 答错 → 产生 answer_records + wrong_records（对 question 为 RESTRICT）
    client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "A", "mode": "normal"},
        headers=auth_headers,
    )
    assert client.get("/api/wrong-records", headers=auth_headers).json() != []

    resp = client.delete(f"/api/workbooks/{workbook['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert client.get(f"/api/workbooks/{workbook['id']}", headers=auth_headers).status_code == 404
    # 相关学习记录随练习册显式删除一并清理
    assert client.get("/api/wrong-records", headers=auth_headers).json() == []


def test_get_system_workbook_readable(client, auth_headers):
    resp = client.get("/api/workbooks/0", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == 0


def test_update_system_workbook_forbidden(client, auth_headers):
    resp = client.put("/api/workbooks/0", json={"name": "hack"}, headers=auth_headers)
    assert resp.status_code == 403


def test_delete_system_workbook_forbidden(client, auth_headers):
    assert client.delete("/api/workbooks/0", headers=auth_headers).status_code == 403


def test_cannot_access_other_users_workbook(client, auth_headers):
    wb = _create(client, auth_headers).json()
    s = uuid.uuid4().hex[:10]
    r2 = client.post(
        "/api/auth/register",
        json={"username": f"x{s}", "email": f"{s}@x.com", "password": "password123"},
    )
    token2 = r2.json()["access_token"]
    resp = client.get(f"/api/workbooks/{wb['id']}", headers={"Authorization": f"Bearer {token2}"})
    assert resp.status_code == 403


def test_requires_auth(client):
    assert client.get("/api/workbooks").status_code == 401
