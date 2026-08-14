"""题目接口测试（CRUD + 选项 + 软删除 + 权限）。"""
from models import Question
from models.enums import QuestionSource, QuestionStatus, QuestionType


def _fill_blank(workbook, **overrides):
    payload = {
        "workbook_id": workbook["id"],
        "type": "fill_blank",
        "content": "求极限 $\\lim_{x\\to0}\\frac{\\sin x}{x}$",
        "answer": "1",
    }
    payload.update(overrides)
    return payload


def _single_choice(workbook):
    return {
        "workbook_id": workbook["id"],
        "type": "single_choice",
        "content": "1+1=?",
        "answer": "B",
        "options": [
            {"option_key": "A", "content": "0", "sort_order": 0},
            {"option_key": "B", "content": "2", "sort_order": 1},
            {"option_key": "C", "content": "3", "sort_order": 2},
            {"option_key": "D", "content": "4", "sort_order": 3},
        ],
    }


# ── 创建 ─────────────────────────────────────────────────
def test_create_fill_blank(client, auth_headers, workbook):
    resp = client.post("/api/questions", json=_fill_blank(workbook), headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["source"] == "user"
    assert data["status"] == "approved"
    assert data["type"] == "fill_blank"
    assert data["options"] == []


def test_create_single_choice_with_options(client, auth_headers, workbook):
    resp = client.post("/api/questions", json=_single_choice(workbook), headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "single_choice"
    assert [o["option_key"] for o in data["options"]] == ["A", "B", "C", "D"]


def test_create_choice_without_options_rejected(client, auth_headers, workbook):
    resp = client.post(
        "/api/questions",
        json=_fill_blank(workbook, type="single_choice"),
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_create_non_choice_with_options_rejected(client, auth_headers, workbook):
    resp = client.post(
        "/api/questions",
        json=_fill_blank(workbook, options=[{"option_key": "A", "content": "x"}]),
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_create_in_system_workbook_forbidden(client, auth_headers):
    resp = client.post(
        "/api/questions",
        json=_fill_blank({"id": 0}),
        headers=auth_headers,
    )
    assert resp.status_code == 403


def test_create_invalid_difficulty(client, auth_headers, workbook):
    resp = client.post(
        "/api/questions", json=_fill_blank(workbook, difficulty=6), headers=auth_headers
    )
    assert resp.status_code == 422


# ── 查询 ─────────────────────────────────────────────────
def test_list_questions_includes_own(client, auth_headers, workbook):
    client.post("/api/questions", json=_fill_blank(workbook), headers=auth_headers)
    resp = client.get("/api/questions", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_questions_by_workbook(client, auth_headers, workbook):
    client.post("/api/questions", json=_fill_blank(workbook), headers=auth_headers)
    resp = client.get(f"/api/questions?workbook_id={workbook['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_question(client, auth_headers, workbook):
    q = client.post("/api/questions", json=_fill_blank(workbook), headers=auth_headers).json()
    resp = client.get(f"/api/questions/{q['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["content"] == q["content"]


def test_list_questions_includes_knowledge_name(client, auth_headers, workbook):
    """题库列表/详情回填 knowledge_name（回归 #9，此前恒为 null）。"""
    node = client.post(
        "/api/knowledge",
        json={"workbook_id": workbook["id"], "name": "极限", "level": 0},
        headers=auth_headers,
    ).json()
    client.post(
        "/api/questions",
        json=_fill_blank(workbook, knowledge_id=node["id"]),
        headers=auth_headers,
    )

    items = client.get(f"/api/questions?workbook_id={workbook['id']}", headers=auth_headers).json()
    assert items[0]["knowledge_name"] == "极限"

    detail = client.get(f"/api/questions/{items[0]['id']}", headers=auth_headers).json()
    assert detail["knowledge_name"] == "极限"


# ── 更新 ─────────────────────────────────────────────────
def test_update_question(client, auth_headers, workbook):
    q = client.post("/api/questions", json=_fill_blank(workbook), headers=auth_headers).json()
    resp = client.put(
        f"/api/questions/{q['id']}", json={"answer": "0"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["answer"] == "0"


def test_update_question_replace_options(client, auth_headers, workbook):
    q = client.post("/api/questions", json=_single_choice(workbook), headers=auth_headers).json()
    resp = client.put(
        f"/api/questions/{q['id']}",
        json={
            "options": [
                {"option_key": "A", "content": "对", "sort_order": 0},
                {"option_key": "B", "content": "错", "sort_order": 1},
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    keys = [o["option_key"] for o in resp.json()["options"]]
    assert keys == ["A", "B"]


# ── 软删除 ───────────────────────────────────────────────
def test_delete_question_is_soft(client, auth_headers, workbook, session):
    q = client.post("/api/questions", json=_fill_blank(workbook), headers=auth_headers).json()
    assert client.delete(f"/api/questions/{q['id']}", headers=auth_headers).status_code == 200
    # 删除后 GET 404
    assert client.get(f"/api/questions/{q['id']}", headers=auth_headers).status_code == 404
    # 列表中不再出现
    assert client.get("/api/questions", headers=auth_headers).json() == []
    # 但物理行仍存在（软删除）
    assert session.get(Question, q["id"]) is not None
    assert session.get(Question, q["id"]).deleted_at is not None


# ── 权限 ─────────────────────────────────────────────────
def test_builtin_question_readonly(client, auth_headers, session):
    q = Question(
        workbook_id=0,
        type=QuestionType.fill_blank,
        content="内置题",
        answer="x",
        source=QuestionSource.builtin,
        status=QuestionStatus.approved,
    )
    session.add(q)
    session.commit()

    assert client.get(f"/api/questions/{q.id}", headers=auth_headers).status_code == 200
    assert (
        client.put(
            f"/api/questions/{q.id}", json={"content": "改"}, headers=auth_headers
        ).status_code
        == 403
    )
    assert client.delete(f"/api/questions/{q.id}", headers=auth_headers).status_code == 403


def test_questions_require_auth(client):
    assert client.get("/api/questions").status_code == 401
