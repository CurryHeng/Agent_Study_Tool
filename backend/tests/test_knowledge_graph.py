"""知识图谱接口测试（#58）。"""


def test_knowledge_graph_returns_tree_edges(client, auth_headers, workbook):
    root = client.post(
        "/api/knowledge",
        json={"workbook_id": workbook["id"], "name": "根", "level": 0},
        headers=auth_headers,
    ).json()
    child = client.post(
        "/api/knowledge",
        json={
            "workbook_id": workbook["id"],
            "parent_id": root["id"],
            "name": "子节点",
            "level": 1,
        },
        headers=auth_headers,
    ).json()

    graph = client.get(
        f"/api/knowledge-graph?workbook_id={workbook['id']}", headers=auth_headers
    ).json()

    assert len(graph["nodes"]) == 2
    node_ids = {n["id"] for n in graph["nodes"]}
    assert root["id"] in node_ids
    assert child["id"] in node_ids

    parent_edges = [e for e in graph["edges"] if e["type"] == "parent"]
    assert any(
        e["source"] == root["id"] and e["target"] == child["id"]
        for e in parent_edges
    )
