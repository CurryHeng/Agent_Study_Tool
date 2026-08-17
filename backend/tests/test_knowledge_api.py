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


# ── P1-2 父节点校验：环检测 / 跨练习册 / 存在性 ──


def _create_workbook(client, headers, name):
    resp = client.post(
        "/api/workbooks", json={"name": name, "description": ""}, headers=headers
    )
    assert resp.status_code == 201
    return resp.json()


def test_update_parent_to_own_descendant_forbidden(client, auth_headers, workbook):
    """把父节点移动到自己的子节点下应被拒绝（否则导图无限递归）。"""
    parent = _create(client, auth_headers, workbook, name="父节点", level=0).json()
    child = _create(
        client, auth_headers, workbook, name="子节点", level=1, parent_id=parent["id"]
    ).json()
    resp = client.put(
        f"/api/knowledge/{parent['id']}",
        json={"parent_id": child["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_update_parent_to_self_forbidden(client, auth_headers, workbook):
    node = _create(client, auth_headers, workbook, name="自环", level=0).json()
    resp = client.put(
        f"/api/knowledge/{node['id']}",
        json={"parent_id": node["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_update_parent_cross_workbook_forbidden(client, auth_headers, workbook):
    """跨练习册挂载父节点应被拒绝（破坏知识树隔离）。"""
    wb2 = _create_workbook(client, auth_headers, "另一个练习册")
    node = _create(client, auth_headers, workbook, name="节点", level=0).json()
    other_parent = _create(client, auth_headers, wb2, name="他册父节点", level=0).json()
    resp = client.put(
        f"/api/knowledge/{node['id']}",
        json={"parent_id": other_parent["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_create_with_cross_workbook_parent_forbidden(client, auth_headers, workbook):
    wb2 = _create_workbook(client, auth_headers, "另一个练习册")
    other_parent = _create(client, auth_headers, wb2, name="他册父节点", level=0).json()
    resp = client.post(
        "/api/knowledge",
        json={
            "workbook_id": workbook["id"],
            "parent_id": other_parent["id"],
            "name": "跨册子节点",
            "level": 1,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_update_parent_missing_forbidden(client, auth_headers, workbook):
    node = _create(client, auth_headers, workbook, name="节点", level=0).json()
    resp = client.put(
        f"/api/knowledge/{node['id']}",
        json={"parent_id": 99999},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_update_parent_within_workbook_ok(client, auth_headers, workbook):
    """同练习册内移动到另一个分支应成功（合法换父节点）。"""
    root_a = _create(client, auth_headers, workbook, name="分支A", level=0).json()
    root_b = _create(client, auth_headers, workbook, name="分支B", level=0).json()
    node = _create(
        client, auth_headers, workbook, name="叶子", level=1, parent_id=root_a["id"]
    ).json()
    resp = client.put(
        f"/api/knowledge/{node['id']}",
        json={"parent_id": root_b["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["parent_id"] == root_b["id"]


# ── P2-3：导图 LLM 分支生成（suggest-children） ──


class _SuggestLLM:
    """返回固定建议的假 LLM。"""

    def __init__(self, raw):
        self._raw = raw
        self.calls = 0

    def generate_json(self, system, user):
        self.calls += 1
        return self._raw


def _mock_suggest(monkeypatch, raw):
    mock = _SuggestLLM(raw)
    # suggest_children 在函数内 import LLMService，需 patch 源模块
    monkeypatch.setattr("services.llm_service.LLMService", lambda: mock)
    return mock


def test_suggest_children_ok(client, auth_headers, workbook, monkeypatch):
    node = _create(client, auth_headers, workbook, name="反向传播", level=0).json()
    _mock_suggest(
        monkeypatch,
        {
            "suggestions": [
                {"name": "链式法则", "description": "求导的链式传递"},
                {"name": "梯度下降", "description": "沿负梯度更新参数"},
                {"name": "学习率", "description": "步长控制"},
            ]
        },
    )
    resp = client.post(
        f"/api/knowledge/{node['id']}/suggest-children", headers=auth_headers
    )
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()["suggestions"]]
    assert names == ["链式法则", "梯度下降", "学习率"]


def test_suggest_children_filters_duplicates(client, auth_headers, workbook, monkeypatch):
    node = _create(client, auth_headers, workbook, name="反向传播", level=0).json()
    _create(
        client, auth_headers, workbook, name="链式法则", level=1, parent_id=node["id"]
    )
    _mock_suggest(
        monkeypatch,
        {
            "suggestions": [
                {"name": "链式法则", "description": "已有，应被过滤"},
                {"name": "梯度下降", "description": "新建议"},
            ]
        },
    )
    resp = client.post(
        f"/api/knowledge/{node['id']}/suggest-children", headers=auth_headers
    )
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()["suggestions"]]
    assert names == ["梯度下降"]


def test_suggest_children_not_configured_503(client, auth_headers, workbook):
    """conftest 已清空 LLM key，无 Mock 时走真实 LLMService 应 503。"""
    node = _create(client, auth_headers, workbook, name="节点", level=0).json()
    resp = client.post(
        f"/api/knowledge/{node['id']}/suggest-children", headers=auth_headers
    )
    assert resp.status_code == 503


def test_suggest_children_foreign_node_403(client, auth_headers, workbook):
    node = _create(client, auth_headers, workbook, name="节点", level=0).json()
    resp = client.post(
        f"/api/knowledge/{node['id']}/suggest-children",
        headers={"Authorization": "Bearer bad-token"},
    )
    assert resp.status_code == 401
