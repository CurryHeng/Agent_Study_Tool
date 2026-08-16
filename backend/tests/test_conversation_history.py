"""会话持久化与学习时间线测试（#46/#47/#59）。"""
from langchain_core.messages import AIMessage


class MockGraph:
    def invoke(self, state, config=None):
        return {"messages": state["messages"] + [AIMessage(content="你好！")]}


def test_conversation_lifecycle(client, auth_headers, monkeypatch):
    from services import agent_service

    monkeypatch.setattr(agent_service, "build_graph", lambda db, user: MockGraph())

    chat = client.post(
        "/api/agent/chat", json={"message": "你好"}, headers=auth_headers
    ).json()
    assert chat["conversation_id"] is not None
    conv_id = chat["conversation_id"]

    conversations = client.get("/api/conversations", headers=auth_headers).json()
    assert any(c["id"] == conv_id for c in conversations)

    messages = client.get(
        f"/api/conversations/{conv_id}/messages", headers=auth_headers
    ).json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "你好！"

    delete = client.delete(f"/api/conversations/{conv_id}", headers=auth_headers)
    assert delete.status_code == 200
    conversations = client.get("/api/conversations", headers=auth_headers).json()
    assert all(c["id"] != conv_id for c in conversations)


def test_history_aggregates_events(client, auth_headers, workbook):
    # 创建题目会生成“添加/生成题目”事件
    q = client.post(
        "/api/questions",
        json={
            "workbook_id": workbook["id"],
            "type": "single_choice",
            "content": "历史事件",
            "answer": "A",
            "options": [
                {"option_key": "A", "content": "1"},
                {"option_key": "B", "content": "2"},
            ],
        },
        headers=auth_headers,
    ).json()
    # 答错会生成“答题”和“错题/复习”事件
    client.post(
        f"/api/questions/{q['id']}/answer",
        json={"user_answer": "B", "mode": "normal"},
        headers=auth_headers,
    )

    history = client.get("/api/history", headers=auth_headers).json()
    assert len(history) >= 2
    types = {h["type"] for h in history}
    assert "generate" in types
    assert "answer" in types
