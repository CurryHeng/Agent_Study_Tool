"""刷题 / 判题 / 错题 / SM-2 测试。"""
from models import AnswerRecord, ReviewCard, WrongRecord
from models.enums import QuestionType
from models.question import Question
from services import grading


def _q(question_type, answer):
    return Question(workbook_id=0, type=question_type, content="c", answer=answer)


# ── 判题（确定性）─────────────────────────────────────────
def test_grade_single_choice():
    q = _q(QuestionType.single_choice, "B")
    assert grading.grade_question(q, "B") is True
    assert grading.grade_question(q, "b") is True
    assert grading.grade_question(q, "A") is False


def test_grade_multiple_choice():
    q = _q(QuestionType.multiple_choice, "ABD")
    assert grading.grade_question(q, "DBA") is True
    assert grading.grade_question(q, "AB") is False


def test_grade_true_false():
    q = _q(QuestionType.true_false, "true")
    assert grading.grade_question(q, "正确") is True
    assert grading.grade_question(q, "false") is False


def test_grade_fill_blank():
    q = _q(QuestionType.fill_blank, "数据")
    assert grading.grade_question(q, "数据") is True
    assert grading.grade_question(q, "  数据 ") is True
    assert grading.grade_question(q, "模型") is False


def test_short_answer_not_auto_gradable():
    q = _q(QuestionType.short_answer, "xxx")
    assert grading.is_auto_gradable(q.type) is False


# ── 简答题 LLM 判分 ───────────────────────────────────────
class _JudgeLLM:
    """按预设结果判题的假 LLM。"""

    def __init__(self, correct):
        self.correct = correct
        self.calls = 0

    def generate_json(self, system, user):
        self.calls += 1
        return {"correct": self.correct}


def test_grade_short_answer_by_llm():
    q = _q(QuestionType.short_answer, "因为时间复杂度是 O(n)")
    assert grading.grade_short_answer(q, "时间复杂度为 O(n)", llm=_JudgeLLM(True)) is True
    assert grading.grade_short_answer(q, "不知道", llm=_JudgeLLM(False)) is False


def test_grade_short_answer_blank_is_wrong_without_llm():
    q = _q(QuestionType.short_answer, "xxx")
    llm = _JudgeLLM(True)
    assert grading.grade_short_answer(q, "   ", llm=llm) is False
    assert llm.calls == 0  # 空白作答不调用 LLM


def test_grade_short_answer_llm_failure_degrades_to_none():
    class BoomLLM:
        def generate_json(self, system, user):
            raise RuntimeError("LLM down")

    q = _q(QuestionType.short_answer, "xxx")
    assert grading.grade_short_answer(q, "随便答", llm=BoomLLM()) is None


def _create_short_answer(client, headers, workbook):
    return client.post(
        "/api/questions",
        json={
            "workbook_id": workbook["id"],
            "type": "short_answer",
            "content": "为什么快速排序平均复杂度是 O(n log n)？",
            "answer": "每次划分将数组分为两部分，递归深度 log n，每层划分 O(n)。",
        },
        headers=headers,
    ).json()


def test_answer_short_answer_llm_correct(
    client, auth_headers, workbook, session, monkeypatch
):
    monkeypatch.setattr(
        "services.llm_service.get_llm", lambda: _JudgeLLM(True)
    )
    q = _create_short_answer(client, auth_headers, workbook)
    resp = client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "每次划分 O(n)，递归 log n 层", "mode": "normal"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_correct"] is True
    # 判对不产生错题记录
    assert session.query(WrongRecord).count() == 0


def test_answer_short_answer_llm_wrong_creates_wrong_record(
    client, auth_headers, workbook, session, monkeypatch
):
    monkeypatch.setattr(
        "services.llm_service.get_llm", lambda: _JudgeLLM(False)
    )
    q = _create_short_answer(client, auth_headers, workbook)
    resp = client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "因为它是 O(1)", "mode": "normal"},
        headers=auth_headers,
    )
    assert resp.json()["is_correct"] is False
    assert session.query(WrongRecord).count() == 1


def test_answer_short_answer_llm_down_degrades_to_self_rating(
    client, auth_headers, workbook, monkeypatch
):
    class BoomLLM:
        def generate_json(self, system, user):
            raise RuntimeError("LLM down")

    monkeypatch.setattr("services.llm_service.get_llm", lambda: BoomLLM())
    q = _create_short_answer(client, auth_headers, workbook)
    resp = client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "分治", "mode": "normal", "rating": "hard"},
        headers=auth_headers,
    )
    data = resp.json()
    assert data["is_correct"] is None  # 降级：不自动判题
    assert data["rating"] == "hard"  # 保留用户自评


# ── 答题流程 ──────────────────────────────────────────────
def _create_choice(client, headers, workbook):
    return client.post(
        "/api/questions",
        json={
            "workbook_id": workbook["id"],
            "type": "single_choice",
            "content": "1+1=?",
            "answer": "B",
            "options": [
                {"option_key": "A", "content": "0"},
                {"option_key": "B", "content": "2"},
                {"option_key": "C", "content": "3"},
                {"option_key": "D", "content": "4"},
            ],
        },
        headers=headers,
    ).json()


def test_answer_correct_flow(client, auth_headers, session, workbook):
    q = _create_choice(client, auth_headers, workbook)

    resp = client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "B", "mode": "normal"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_correct"] is True
    assert data["rating"] == "good"
    assert data["card"]["state"] in ("Learning", "Review")  # FSRS 状态
    assert data["card"]["total_correct"] == 1

    records = session.query(AnswerRecord).filter(AnswerRecord.question_id == q["id"]).all()
    assert len(records) == 1
    assert records[0].is_correct == 1
    assert records[0].mode == "normal"


def test_answer_wrong_creates_wrong_record(client, auth_headers, session, workbook):
    q = _create_choice(client, auth_headers, workbook)

    resp = client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "A", "mode": "normal"},
        headers=auth_headers,
    )
    assert resp.json()["is_correct"] is False
    assert resp.json()["rating"] == "again"

    wrong = session.query(WrongRecord).filter(WrongRecord.question_id == q["id"]).all()
    assert len(wrong) == 1
    assert wrong[0].wrong_answer == "A"


def test_answer_updates_fsrs_card(client, auth_headers, session, workbook):
    q = _create_choice(client, auth_headers, workbook)
    client.post(f"/api/questions/{q['id']}/answer", json={"user_answer": "B"}, headers=auth_headers)
    client.post(f"/api/questions/{q['id']}/answer", json={"user_answer": "A"}, headers=auth_headers)

    card = session.query(ReviewCard).filter(ReviewCard.question_id == q["id"]).first()
    assert card.total_attempts == 2
    assert card.total_correct == 1  # 第一次正确，第二次错误
    assert card.state in ("Learning", "Relearning")  # FSRS: 答错回到学习态


def test_strict_mode_forces_auto_rating(client, auth_headers, workbook):
    q = _create_choice(client, auth_headers, workbook)
    resp = client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "B", "mode": "strict", "rating": "again"},
        headers=auth_headers,
    )
    data = resp.json()
    assert data["is_correct"] is True
    assert data["rating"] == "good"  # strict 强制派生，忽略客户端评分


def test_get_due(client, auth_headers, workbook):
    q = _create_choice(client, auth_headers, workbook)
    resp = client.get("/api/review/due", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert any(item["question"]["id"] == q["id"] for item in items)


def test_update_wrong_record_reason(client, auth_headers, workbook):
    q = _create_choice(client, auth_headers, workbook)
    client.post(f"/api/questions/{q['id']}/answer", json={"user_answer": "A"}, headers=auth_headers)

    records = client.get("/api/wrong-records", headers=auth_headers).json()
    assert len(records) == 1
    assert records[0]["wrong_reason"] is None

    resp = client.put(
        f"/api/wrong-records/{records[0]['id']}",
        json={"wrong_reason": "粗心大意"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["wrong_reason"] == "粗心大意"

    refreshed = client.get("/api/wrong-records", headers=auth_headers).json()
    assert refreshed[0]["wrong_reason"] == "粗心大意"


def test_update_wrong_record_can_clear_field(client, auth_headers, workbook):
    """显式传 null 应清空字段（修复：None 此前被当作"未修改"）。"""
    q = _create_choice(client, auth_headers, workbook)
    client.post(f"/api/questions/{q['id']}/answer", json={"user_answer": "A"}, headers=auth_headers)
    records = client.get("/api/wrong-records", headers=auth_headers).json()
    rid = records[0]["id"]

    client.put(f"/api/wrong-records/{rid}", json={"wrong_reason": "粗心"}, headers=auth_headers)
    resp = client.put(
        f"/api/wrong-records/{rid}", json={"wrong_reason": None}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["wrong_reason"] is None  # 已清空
    assert resp.json()["wrong_answer"] is not None  # 未传字段不受影响


def test_wrong_records_exclude_soft_deleted_questions(client, auth_headers, workbook):
    """软删题目后，其错题记录不应再出现在错题本。"""
    q = _create_choice(client, auth_headers, workbook)
    client.post(f"/api/questions/{q['id']}/answer", json={"user_answer": "A"}, headers=auth_headers)
    assert len(client.get("/api/wrong-records", headers=auth_headers).json()) == 1

    client.delete(f"/api/questions/{q['id']}", headers=auth_headers)
    assert client.get("/api/wrong-records", headers=auth_headers).json() == []


def test_update_wrong_record_forbidden_for_other_user(client, auth_headers, workbook):
    import uuid

    q = _create_choice(client, auth_headers, workbook)
    client.post(f"/api/questions/{q['id']}/answer", json={"user_answer": "A"}, headers=auth_headers)
    records = client.get("/api/wrong-records", headers=auth_headers).json()
    rid = records[0]["id"]

    s = uuid.uuid4().hex[:10]
    other = client.post(
        "/api/auth/register",
        json={"username": f"x{s}", "email": f"{s}@x.com", "password": "password123"},
    ).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    resp = client.put(
        f"/api/wrong-records/{rid}", json={"wrong_reason": "hack"}, headers=other_headers
    )
    assert resp.status_code == 403


def test_toggle_favorite(client, auth_headers, workbook):
    q = _create_choice(client, auth_headers, workbook)
    card = client.post(f"/api/review/{q['id']}/favorite", headers=auth_headers).json()
    assert card["favorited"] == 1
    card2 = client.post(f"/api/review/{q['id']}/favorite", headers=auth_headers).json()
    assert card2["favorited"] == 0


def test_get_due_favorites(client, auth_headers, workbook):
    q = _create_choice(client, auth_headers, workbook)
    client.post(f"/api/review/{q['id']}/favorite", headers=auth_headers)

    favs = client.get("/api/review/due?favorites=true", headers=auth_headers).json()
    assert any(item["question"]["id"] == q["id"] for item in favs)

    client.post(f"/api/review/{q['id']}/favorite", headers=auth_headers)
    favs2 = client.get("/api/review/due?favorites=true", headers=auth_headers).json()
    assert not any(item["question"]["id"] == q["id"] for item in favs2)


# ── 学习统计 ──────────────────────────────────────────────
def test_stats_endpoint(client, auth_headers, workbook):
    q = _create_choice(client, auth_headers, workbook)
    for ans in ("B", "A"):
        client.post(
            f"/api/questions/{q['id']}/answer",
            json={"user_answer": ans, "mode": "normal"},
            headers=auth_headers,
        )

    resp = client.get("/api/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["question_total"] >= 1
    assert data["cards_total"] >= 1
    assert data["mastery"]["again"] >= 1
    assert data["mastery"]["good"] >= 1
    assert data["accuracy_buckets"] and data["accuracy_buckets"][0]["label"] == "0-19%"
    assert len(data["recent"]) == 2
    assert data["recent"][0]["question_id"] == q["id"]
    assert data["knowledge_heatmap"] is not None
    assert data["wrong_reasons"] is not None


def test_stats_endpoint_requires_auth(client):
    resp = client.get("/api/stats")
    assert resp.status_code in (401, 403)


def test_stats_isolated_between_users_on_builtin_questions(client, auth_headers, session):
    """内置题库（workbook_id=0 全员可见）的复习卡不能跨用户统计（回归 #1）。"""
    import uuid

    from models import Question
    from models.enums import QuestionSource, QuestionStatus, QuestionType

    q = Question(
        workbook_id=0,
        type=QuestionType.single_choice,
        content="1+1=?",
        answer="B",
        difficulty=1,
        source=QuestionSource.builtin,
        status=QuestionStatus.approved,
    )
    session.add(q)
    session.flush()

    # 用户 A 答过这道内置题 → A 的复习卡
    client.post(
        f"/api/questions/{q.id}/answer",
        json={"user_answer": "B", "mode": "normal"},
        headers=auth_headers,
    )

    # 用户 B 也答同一道题
    s = uuid.uuid4().hex[:10]
    other = client.post(
        "/api/auth/register",
        json={"username": f"s{s}", "email": f"{s}@x.com", "password": "password123"},
    ).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    client.post(
        f"/api/questions/{q.id}/answer",
        json={"user_answer": "B", "mode": "normal"},
        headers=other_headers,
    )

    # B 的统计只能包含 B 自己的 1 张卡，不能混入 A 的卡
    stats_b = client.get("/api/stats", headers=other_headers).json()
    assert stats_b["cards_total"] == 1
    stats_a = client.get("/api/stats", headers=auth_headers).json()
    assert stats_a["cards_total"] == 1
