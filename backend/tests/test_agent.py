"""Navigator + Orchestrator（LangGraph）图流程测试（对齐详细设计）。"""
import pytest

from models import AgentTask, User
from models.enums import AgentTaskStatus
from services import access, agent_service


class MockLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate_json(self, system, user):
        self.calls += 1
        if not self.responses:
            return {"intent": "chat", "params": {}}
        return self.responses.pop(0)


def _user(session, registered_user):
    return session.get(User, registered_user["user"]["id"])


def _nav(intent, params=None):
    return MockLLM([{"intent": intent, "params": params or {}}])


def _choice(content="1+1=?", answer="B"):
    return {
        "type": "single_choice",
        "content": content,
        "answer": answer,
        "options": [
            {"option_key": "A", "content": "0"},
            {"option_key": "B", "content": "2"},
            {"option_key": "C", "content": "3"},
            {"option_key": "D", "content": "4"},
        ],
    }


def _pass_review(question, params):
    return True


def _echo_save(params, questions):
    return [{"content": q.content, "answer": q.answer} for q in questions]


# ── 意图路由 ─────────────────────────────────────────────
def test_generate_questions_intent(client, auth_headers, registered_user, session, workbook):
    user = _user(session, registered_user)
    nav = _nav("generate_questions", {"workbook_id": workbook["id"], "count": 2})

    def fake_generate(params):
        return [_choice("1+1=?"), _choice("2+2=?", "C")]

    result = agent_service.run_task(
        session,
        user,
        "帮我出2道选择题",
        navigator_llm=nav,
        generate_fn=fake_generate,
        review_fn=_pass_review,
        save_fn=_echo_save,
    )
    assert result["intent"] == "generate_questions"
    assert len(result["result"]["questions"]) == 2


def test_generate_mindmap_intent(client, auth_headers, registered_user, session, workbook):
    user = _user(session, registered_user)
    client.post(
        "/api/knowledge",
        json={"workbook_id": workbook["id"], "name": "第一章", "level": 0},
        headers=auth_headers,
    )
    nav = _nav("generate_mindmap", {"workbook_id": workbook["id"]})

    result = agent_service.run_task(session, user, "生成思维导图", navigator_llm=nav)
    assert result["intent"] == "generate_mindmap"
    root = result["result"]["mindmap"]["root"]
    assert root["label"] == workbook["name"]
    assert len(root["children"]) == 1


def test_list_documents_intent(client, auth_headers, registered_user, session, workbook):
    user = _user(session, registered_user)
    nav = _nav("list_documents", {"workbook_id": workbook["id"]})

    result = agent_service.run_task(session, user, "列出文档", navigator_llm=nav)
    assert result["intent"] == "list_documents"
    assert result["result"]["documents"] == []


def test_chat_intent_direct_answer(client, auth_headers, registered_user, session):
    user = _user(session, registered_user)
    nav = MockLLM(
        [
            {"intent": "chat", "params": {}},  # navigator
            {"reply": "你好，我是 StudyForge 助手"},  # direct_answer（LLM 回答）
        ]
    )

    result = agent_service.run_task(session, user, "你好", navigator_llm=nav)
    assert result["intent"] == "chat"
    assert result["result"]["reply"] == "你好，我是 StudyForge 助手"


def test_unknown_intent_falls_back_to_chat(client, auth_headers, registered_user, session):
    user = _user(session, registered_user)
    nav = _nav("unknown_intent")

    result = agent_service.run_task(session, user, "随便聊聊", navigator_llm=nav)
    assert result["intent"] == "chat"


# ── 重试机制（Review FAIL 回环，最多 2 次）─────────────────
def test_question_retry_then_success(client, auth_headers, registered_user, session, workbook):
    user = _user(session, registered_user)
    nav = _nav("generate_questions", {"workbook_id": workbook["id"], "count": 1})
    calls = []

    def flaky_generate(params):
        calls.append(1)
        if len(calls) < 3:
            return []
        return [_choice("1+1=?")]

    result = agent_service.run_task(
        session,
        user,
        "出题",
        navigator_llm=nav,
        generate_fn=flaky_generate,
        review_fn=_pass_review,
        save_fn=_echo_save,
    )
    assert len(result["result"]["questions"]) == 1
    assert len(calls) == 3  # 初始 + 2 次重试


def test_question_retry_exhausted(client, auth_headers, registered_user, session, workbook):
    user = _user(session, registered_user)
    nav = _nav("generate_questions", {"workbook_id": workbook["id"], "count": 1})

    def always_empty(params):
        return []

    result = agent_service.run_task(
        session,
        user,
        "出题",
        navigator_llm=nav,
        generate_fn=always_empty,
        review_fn=_pass_review,
        save_fn=_echo_save,
    )
    assert result["result"]["questions"] == []


# ── API 入口 ─────────────────────────────────────────────
def test_agent_chat_endpoint(client, auth_headers, monkeypatch):
    from workflow import graph

    monkeypatch.setattr(graph, "get_llm", lambda: _nav("chat"))
    resp = client.post("/api/agent/chat", json={"message": "你好"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "chat"
    assert "reply" in data["result"]


# ── 兜底与任务日志 ───────────────────────────────────────
def test_missing_workbook_id_friendly_error(client, auth_headers, registered_user, session):
    """LLM 未返回 workbook_id 且无 hint 时，友好 400 而非 KeyError→500（回归 #5）。"""
    user = _user(session, registered_user)
    nav = _nav("generate_questions")  # params 无 workbook_id

    with pytest.raises(access.AccessError) as exc_info:
        agent_service.run_task(
            session,
            user,
            "出题",
            navigator_llm=nav,
            generate_fn=lambda params: [_choice("1+1=?")],
            review_fn=_pass_review,
            # save_fn 用真实实现 → 触发 workbook_id 兜底校验
        )
    assert exc_info.value.status_code == 400


def test_agent_task_recorded_failed_on_error(
    client, auth_headers, registered_user, session, workbook
):
    """执行异常的任务应记为 failed，而非恒记 success（回归 #7）。"""
    user = _user(session, registered_user)
    nav = _nav("generate_questions", {"workbook_id": workbook["id"]})

    def boom(params):
        raise RuntimeError("LLM down")

    with pytest.raises(RuntimeError):
        agent_service.run_task(
            session, user, "出题", navigator_llm=nav, generate_fn=boom,
            review_fn=_pass_review, save_fn=_echo_save,
        )

    task = (
        session.query(AgentTask)
        .filter(AgentTask.user_id == user.id)
        .order_by(AgentTask.id.desc())
        .first()
    )
    assert task is not None
    assert task.status == AgentTaskStatus.failed
    assert "LLM down" in (task.error_message or "")


def test_agent_task_recorded_success(client, auth_headers, registered_user, session):
    user = _user(session, registered_user)
    nav = _nav("chat")

    agent_service.run_task(session, user, "你好", navigator_llm=nav)

    task = (
        session.query(AgentTask)
        .filter(AgentTask.user_id == user.id)
        .order_by(AgentTask.id.desc())
        .first()
    )
    assert task is not None
    assert task.status == AgentTaskStatus.success
