"""核心学习闭环端到端集成测试（登录 → 题库 → 刷题 → 判题 → 错题 → Agent）。"""

from langchain_core.messages import AIMessage


class MockGraph:
    def invoke(self, state, config=None):
        return {"messages": state["messages"] + [AIMessage(content="你好！")]}


def test_full_learning_loop(client, registered_user, monkeypatch):
    creds = registered_user["creds"]

    # 1. 登录
    login = client.post(
        "/api/auth/login", json={"email": creds["email"], "password": creds["password"]}
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 2. 创建练习册
    wb = client.post("/api/workbooks", json={"name": "高等数学"}, headers=headers).json()

    # 3. 创建选择题
    q = client.post(
        "/api/questions",
        json={
            "workbook_id": wb["id"],
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

    # 4. 题库列表
    questions = client.get(f"/api/questions?workbook_id={wb['id']}", headers=headers).json()
    assert len(questions) == 1

    # 5. 待复习（新题卡片 today 到期，答题前检查）
    due = client.get("/api/review/due", headers=headers).json()
    assert any(item["question"]["id"] == q["id"] for item in due)

    # 6. 刷题：正确作答
    correct = client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "B", "mode": "normal"},
        headers=headers,
    ).json()
    assert correct["is_correct"] is True

    # 7. 刷题：错误作答 → 生成错题
    wrong = client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "A", "mode": "normal"},
        headers=headers,
    ).json()
    assert wrong["is_correct"] is False

    # 8. 错题本
    wrong_records = client.get("/api/wrong-records", headers=headers).json()
    assert len(wrong_records) == 1
    assert wrong_records[0]["correct_answer"] == "B"
    assert wrong_records[0]["wrong_answer"] == "A"

    # 9. Agent 基础入口（mock ReAct 图，测试中不调用真实模型）
    from services import agent_service

    monkeypatch.setattr(agent_service, "build_graph", lambda db, user: MockGraph())
    chat = client.post("/api/agent/chat", json={"message": "你好"}, headers=headers).json()
    assert chat["intent"] == "chat"
    assert chat["reply"] == "你好！"
