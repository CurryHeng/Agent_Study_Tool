"""分页与筛选接口测试（#53/#54）。"""


def _create_choice(client, headers, workbook):
    return client.post(
        "/api/questions",
        json={
            "workbook_id": workbook["id"],
            "type": "single_choice",
            "content": "选择",
            "answer": "A",
            "options": [
                {"option_key": "A", "content": "1"},
                {"option_key": "B", "content": "2"},
            ],
        },
        headers=headers,
    ).json()


def _create_fill(client, headers, workbook):
    return client.post(
        "/api/questions",
        json={
            "workbook_id": workbook["id"],
            "type": "fill_blank",
            "content": "填空",
            "answer": "数据",
        },
        headers=headers,
    ).json()


def _answer_wrong(client, headers, qid, answer="X"):
    client.post(
        f"/api/questions/{qid}/answer",
        json={"user_answer": answer, "mode": "normal"},
        headers=headers,
    )


def test_wrong_records_pagination_and_type_filter(client, auth_headers, workbook):
    q1 = _create_choice(client, auth_headers, workbook)
    q2 = _create_fill(client, auth_headers, workbook)
    _answer_wrong(client, auth_headers, q1["id"], "B")
    _answer_wrong(client, auth_headers, q2["id"], "错")

    all_records = client.get("/api/wrong-records", headers=auth_headers).json()
    assert len(all_records) == 2

    filtered = client.get(
        "/api/wrong-records?question_type=single_choice", headers=auth_headers
    ).json()
    assert len(filtered) == 1
    assert filtered[0]["question_type"] == "single_choice"

    page1 = client.get("/api/wrong-records?page=1&page_size=1", headers=auth_headers).json()
    page2 = client.get("/api/wrong-records?page=2&page_size=1", headers=auth_headers).json()
    assert len(page1) == 1
    assert len(page2) == 1
    assert page1[0]["id"] != page2[0]["id"]


def test_questions_pagination(client, auth_headers, workbook):
    for _ in range(3):
        _create_choice(client, auth_headers, workbook)

    page1 = client.get("/api/questions?page=1&page_size=2", headers=auth_headers).json()
    page2 = client.get("/api/questions?page=2&page_size=2", headers=auth_headers).json()
    assert len(page1) == 2
    assert len(page2) == 1


def test_with_total_envelope(client, auth_headers, workbook):
    """with_total=true 返回 {total, items} 信封，供前端精确计算总页数（修复"下一页"无上限）。"""
    qs = [_create_choice(client, auth_headers, workbook) for _ in range(3)]
    _answer_wrong(client, auth_headers, qs[0]["id"], "B")

    q = client.get(
        "/api/questions?page=1&page_size=2&with_total=true", headers=auth_headers
    ).json()
    assert q["total"] == 3
    assert len(q["items"]) == 2

    w = client.get(
        "/api/wrong-records?page=1&page_size=1&with_total=true", headers=auth_headers
    ).json()
    assert w["total"] == 1
    assert len(w["items"]) == 1

    # 不带 with_total 时行为不变（纯数组，向后兼容）
    legacy = client.get("/api/questions?page=1&page_size=2", headers=auth_headers).json()
    assert isinstance(legacy, list)


def test_knowledge_pagination(client, auth_headers, workbook):
    for i in range(3):
        client.post(
            "/api/knowledge",
            json={"workbook_id": workbook["id"], "name": f"节点{i}", "level": 0},
            headers=auth_headers,
        )

    page1 = client.get(
        f"/api/knowledge?workbook_id={workbook['id']}&page=1&page_size=2",
        headers=auth_headers,
    ).json()
    page2 = client.get(
        f"/api/knowledge?workbook_id={workbook['id']}&page=2&page_size=2",
        headers=auth_headers,
    ).json()
    assert len(page1) == 2
    assert len(page2) == 1
