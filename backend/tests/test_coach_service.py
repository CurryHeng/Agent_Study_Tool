"""错因分析（coach_service + wrong_records 错因字段）测试。"""
from models import WrongRecord


class _CoachLLM:
    def __init__(self, result=None):
        self.result = result or {
            "reason_type": "概念不清",
            "explanation": "对核心概念理解不到位",
            "suggestion": "重新阅读教材相关章节",
        }
        self.calls = 0

    def generate_json(self, system, user):
        self.calls += 1
        return self.result


def _create_wrong(client, headers, workbook):
    """建一道选择题并答错，返回错题记录。"""
    q = client.post(
        "/api/questions",
        json={
            "workbook_id": workbook["id"],
            "type": "single_choice",
            "content": "1+1=?",
            "answer": "B",
            "options": [
                {"option_key": "A", "content": "0"},
                {"option_key": "B", "content": "2"},
            ],
        },
        headers=headers,
    ).json()
    client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "A", "mode": "normal"},
        headers=headers,
    )
    records = client.get("/api/wrong-records", headers=headers).json()
    return records[0]


def test_analyze_wrong_reason_persists_and_aggregatable(
    client, auth_headers, workbook, session, monkeypatch
):
    monkeypatch.setattr("services.llm_service.get_llm", lambda: _CoachLLM())
    record = _create_wrong(client, auth_headers, workbook)

    resp = client.post(
        f"/api/wrong-records/{record['id']}/analyze", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reason_type"] == "概念不清"
    assert data["explanation"] == "对核心概念理解不到位"
    assert data["suggestion"] == "重新阅读教材相关章节"

    # 落库
    wr = session.get(WrongRecord, record["id"])
    assert wr.reason_type == "概念不清"
    assert wr.ai_explanation == "对核心概念理解不到位"
    assert wr.ai_suggestion == "重新阅读教材相关章节"

    # 列表可聚合（reason_type 出现在列表响应里）
    listed = client.get("/api/wrong-records", headers=auth_headers).json()
    assert listed[0]["reason_type"] == "概念不清"
    assert listed[0]["explanation"] == "对核心概念理解不到位"


def test_analyze_invalid_reason_type_falls_back_to_other(
    client, auth_headers, workbook, session, monkeypatch
):
    monkeypatch.setattr(
        "services.llm_service.get_llm",
        lambda: _CoachLLM({"reason_type": "瞎编的", "explanation": "x", "suggestion": "y"}),
    )
    record = _create_wrong(client, auth_headers, workbook)
    resp = client.post(
        f"/api/wrong-records/{record['id']}/analyze", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["reason_type"] == "其他"
    assert session.get(WrongRecord, record["id"]).reason_type == "其他"


def test_analyze_forbidden_for_other_user(client, auth_headers, workbook):
    import uuid

    record = _create_wrong(client, auth_headers, workbook)
    s = uuid.uuid4().hex[:10]
    other = client.post(
        "/api/auth/register",
        json={"username": f"x{s}", "email": f"{s}@x.com", "password": "password123"},
    ).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    resp = client.post(
        f"/api/wrong-records/{record['id']}/analyze", headers=other_headers
    )
    assert resp.status_code == 403


def test_analyze_missing_record_returns_404(client, auth_headers):
    resp = client.post("/api/wrong-records/999999/analyze", headers=auth_headers)
    assert resp.status_code == 404


def test_analyze_llm_not_configured_returns_503(client, auth_headers, workbook):
    record = _create_wrong(client, auth_headers, workbook)
    # conftest 清空了 key 且隔离了 ai_settings.json，未 mock 时应返回 503
    resp = client.post(
        f"/api/wrong-records/{record['id']}/analyze", headers=auth_headers
    )
    assert resp.status_code == 503


def test_analyze_llm_failure_returns_500(client, auth_headers, workbook, monkeypatch):
    class BoomLLM:
        def generate_json(self, system, user):
            raise RuntimeError("LLM down")

    monkeypatch.setattr("services.llm_service.get_llm", lambda: BoomLLM())
    record = _create_wrong(client, auth_headers, workbook)
    resp = client.post(
        f"/api/wrong-records/{record['id']}/analyze", headers=auth_headers
    )
    assert resp.status_code == 500
