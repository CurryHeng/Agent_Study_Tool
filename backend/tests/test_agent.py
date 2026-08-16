"""主 Agent ReAct 图、工具调用轨迹与任务日志测试。"""
import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import ValidationError

from models import AgentTask, Knowledge, Question, User
from models.enums import AgentTaskStatus
from schemas.generation import GeneratedQuestion, ReviewResult
from services import agent_service, generation_service
from services.access import AccessError
from workflow.graph import RECURSION_LIMIT
from workflow.tools import GenerateInput, build_tools


class FakeGraph:
    def __init__(self, messages=None, error=None):
        self.messages = messages or []
        self.error = error
        self.input = None
        self.config = None

    def invoke(self, state, config=None):
        self.input = state
        self.config = config
        if self.error:
            raise self.error
        return {"messages": state["messages"] + self.messages}


def _user(session, registered_user):
    return session.get(User, registered_user["user"]["id"])


def _tool_messages():
    return [
        AIMessage(content="", tool_calls=[{
            "name": "search_documents", "args": {"workbook_id": 3, "query": "ReAct"},
            "id": "call-1", "type": "tool_call",
        }]),
        ToolMessage(content='[{"content":"ReAct combines reasoning and acting"}]',
                    tool_call_id="call-1", name="search_documents"),
        AIMessage(content="已根据资料整理完成。"),
    ]


def test_react_tool_calls_are_exposed_as_steps(session, registered_user):
    user = _user(session, registered_user)
    result = agent_service.run_task(
        session, user, "整理 ReAct", 3, graph=FakeGraph(_tool_messages())
    )
    assert result["reply"] == "已根据资料整理完成。"
    assert result["intent"] == "search_documents"
    assert result["steps"] == [{
        "id": 1,
        "tool": "search_documents", "args": {"workbook_id": 3, "query": "ReAct"},
        "status": "success", "ok": True, "summary": "返回 1 项", "error": None,
    }]
    assert result["status"] == "completed"
    assert result["error"] is None
    assert result["proposals"] == []
    assert result["navigate"] is None


def test_workbook_hint_is_injected_and_iteration_limit_applied(session, registered_user):
    user = _user(session, registered_user)
    graph = FakeGraph([AIMessage(content="好的")])
    agent_service.run_task(session, user, "列出资料", 42, graph=graph)
    first = graph.input["messages"][0]
    assert isinstance(first, HumanMessage)
    assert "当前练习册 ID：42" in first.content
    assert graph.config == {"recursion_limit": RECURSION_LIMIT}
    assert RECURSION_LIMIT == 17


def test_direct_chat_has_no_fake_steps(session, registered_user):
    user = _user(session, registered_user)
    result = agent_service.run_task(
        session, user, "你好", graph=FakeGraph([AIMessage(content="你好！")])
    )
    assert result["intent"] == "chat"
    assert result["steps"] == []
    assert result["result"]["reply"] == "你好！"


def test_failed_tool_step_is_marked_not_ok(session, registered_user):
    user = _user(session, registered_user)
    messages = [
        AIMessage(content="", tool_calls=[{
            "name": "get_knowledge_tree", "args": {"workbook_id": 9},
            "id": "bad", "type": "tool_call",
        }]),
        ToolMessage(content="无权访问", tool_call_id="bad", name="get_knowledge_tree",
                    status="error"),
        AIMessage(content="无法读取该练习册。"),
    ]
    result = agent_service.run_task(session, user, "读取", graph=FakeGraph(messages))
    assert result["steps"][0]["ok"] is False
    assert result["steps"][0]["status"] == "failed"
    assert result["steps"][0]["error"] == "无权访问"


def test_generate_step_has_structured_summary(session, registered_user):
    user = _user(session, registered_user)
    messages = [
        AIMessage(content="", tool_calls=[{
            "name": "generate_questions",
            "args": {"workbook_id": 0, "topic": "ReAct", "count": 10},
            "id": "generate", "type": "tool_call",
        }]),
        ToolMessage(
            content=json.dumps({
                "proposal_id": "proposal-1",
                "action": "generate_questions",
                "target": {"workbook_id": 1},
                "changes": {"before": None, "after": {"questions": []}},
                "impact": "向题库新增 10 道审核通过的题目",
                "expires_in_sec": 600,
            }, ensure_ascii=False),
            tool_call_id="generate",
            name="generate_questions",
        ),
        AIMessage(content="已生成预览。"),
    ]
    result = agent_service.run_task(session, user, "出 10 道题", graph=FakeGraph(messages))
    assert result["steps"][0]["summary"] == "向题库新增 10 道审核通过的题目"
    assert result["proposals"][0]["proposal_id"] == "proposal-1"
    assert result["status"] == "waiting_confirm"


def test_page_entity_context_resolves_here(session, registered_user):
    user = _user(session, registered_user)
    graph = FakeGraph([AIMessage(content="将修改当前知识点。")])
    agent_service.run_task(
        session,
        user,
        "把这里改简单点",
        conversation_id=None,
        context={
            "route": "/mindmap",
            "entity": {"type": "knowledge_node", "id": 16},
        },
        graph=graph,
    )
    prompt = graph.input["messages"][-1]
    assert isinstance(prompt, HumanMessage)
    assert "当前页面路由：/mindmap" in prompt.content
    assert "type=knowledge_node, id=16" in prompt.content
    assert "这里" in prompt.content


def test_previous_messages_are_loaded_for_multiturn(session, registered_user):
    user = _user(session, registered_user)
    first_graph = FakeGraph([AIMessage(content="已生成 5 道 ReAct 基础题。")])
    first = agent_service.run_task(
        session, user, "生成 5 道 ReAct 基础题", graph=first_graph
    )

    second_graph = FakeGraph([AIMessage(content="已继续生成 5 道难题。")])
    agent_service.run_task(
        session,
        user,
        "再来 5 道难的",
        conversation_id=first["conversation_id"],
        graph=second_graph,
    )

    messages = second_graph.input["messages"]
    assert [type(message) for message in messages] == [
        HumanMessage,
        AIMessage,
        HumanMessage,
    ]
    assert messages[0].content == "生成 5 道 ReAct 基础题"
    assert messages[1].content == "已生成 5 道 ReAct 基础题。"
    assert messages[2].content == "再来 5 道难的"


def test_agent_task_records_structured_result(session, registered_user):
    user = _user(session, registered_user)
    result = agent_service.run_task(session, user, "整理", graph=FakeGraph(_tool_messages()))
    task = session.query(AgentTask).order_by(AgentTask.id.desc()).first()
    assert task.status == AgentTaskStatus.success
    stored = json.loads(task.result_data)
    assert stored["task_id"] == result["task_id"]
    assert stored["steps"][0]["tool"] == "search_documents"


def test_agent_task_records_failure(session, registered_user):
    user = _user(session, registered_user)
    with pytest.raises(RuntimeError, match="model down"):
        agent_service.run_task(
            session, user, "整理", graph=FakeGraph(error=RuntimeError("model down"))
        )
    task = session.query(AgentTask).order_by(AgentTask.id.desc()).first()
    assert task.status == AgentTaskStatus.failed
    assert "model down" in task.error_message


def test_generate_tool_requires_semantic_topic():
    schema = GenerateInput.model_json_schema()
    assert "topic" in schema["required"]
    assert "明确的出题主题" in schema["properties"]["topic"]["description"]
    with pytest.raises(ValidationError):
        GenerateInput(workbook_id=1, count=10)


def test_generate_preview_retries_and_rejects_failed_review(monkeypatch):
    question = GeneratedQuestion(
        type="true_false", content="ReAct 包含行动。", answer="true"
    )
    generate_calls = []
    review_results = iter([
        ReviewResult(passed=False), ReviewResult(passed=False), ReviewResult(passed=True)
    ])

    def fake_generate(*args, **kwargs):
        generate_calls.append(1)
        return [question]

    monkeypatch.setattr(generation_service, "generate_batch", fake_generate)
    monkeypatch.setattr(
        generation_service, "review_question", lambda *args, **kwargs: next(review_results)
    )
    result = generation_service.generate_preview(
        object(), "Agent", "ReAct", question.type, 1, 1, "context"
    )
    assert result == [question]
    assert len(generate_calls) == 3


def test_tools_include_read_layer_and_enforce_permissions(session, registered_user):
    user = _user(session, registered_user)
    tools = {tool.name: tool for tool in build_tools(session, user, object())}
    assert {"search_documents", "get_knowledge_tree", "get_knowledge_detail",
            "list_documents", "get_questions", "generate_questions",
            "add_knowledge_node", "update_knowledge_node",
            "delete_knowledge_node"} <= set(tools)
    with pytest.raises(AccessError):
        tools["get_knowledge_tree"].invoke({"workbook_id": 999999})


def test_agent_chat_endpoint_contract(client, auth_headers, monkeypatch):
    graph = FakeGraph([AIMessage(content="你好，我是 EStudy 助手")])
    monkeypatch.setattr(agent_service, "build_graph", lambda db, user: graph)
    response = client.post("/api/agent/chat", json={"message": "你好"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["reply"]
    assert data["steps"] == []
    assert data["proposals"] == []
    assert data["navigate"] is None
    assert data["intent"] == "chat"
    assert data["status"] == "completed"
    assert data["error"] is None


def test_agent_chat_rejects_unknown_context_entity(client, auth_headers):
    response = client.post(
        "/api/agent/chat",
        json={
            "message": "处理这里",
            "context": {"entity": {"type": "unknown", "id": 1}},
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_delete_proposal_does_not_write_until_confirmed(
    client, session, registered_user, auth_headers, workbook
):
    user = _user(session, registered_user)
    create_response = client.post(
        "/api/knowledge",
        json={"workbook_id": workbook["id"], "name": "待删除知识点", "level": 0},
        headers=auth_headers,
    )
    knowledge_id = create_response.json()["id"]
    tools = {tool.name: tool for tool in build_tools(session, user, object())}

    proposal = tools["delete_knowledge_node"].invoke({"knowledge_id": knowledge_id})
    assert proposal["action"] == "delete_knowledge_node"
    assert proposal["expires_in_sec"] == 600
    assert session.get(Knowledge, knowledge_id) is not None

    response = client.post(
        "/api/agent/confirm",
        json={"proposal_id": proposal["proposal_id"], "approved": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["result"] == {"deleted": True, "knowledge_id": knowledge_id}
    assert session.get(Knowledge, knowledge_id) is None

    replay = client.post(
        "/api/agent/confirm",
        json={"proposal_id": proposal["proposal_id"], "approved": True},
        headers=auth_headers,
    )
    assert replay.status_code == 404


def test_rejected_proposal_is_discarded(
    client, session, registered_user, auth_headers, workbook
):
    user = _user(session, registered_user)
    node = client.post(
        "/api/knowledge",
        json={"workbook_id": workbook["id"], "name": "保留知识点", "level": 0},
        headers=auth_headers,
    ).json()
    tools = {tool.name: tool for tool in build_tools(session, user, object())}
    proposal = tools["delete_knowledge_node"].invoke({"knowledge_id": node["id"]})

    response = client.post(
        "/api/agent/confirm",
        json={"proposal_id": proposal["proposal_id"], "approved": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["result"] == {"approved": False}
    assert session.get(Knowledge, node["id"]) is not None


def test_generate_proposal_saves_only_after_confirm(
    client, session, monkeypatch, registered_user, auth_headers, workbook
):
    user = _user(session, registered_user)
    generated = GeneratedQuestion(
        type="true_false", content="ReAct 会调用工具。", answer="true"
    )
    monkeypatch.setattr(
        generation_service, "generate_preview", lambda *args, **kwargs: [generated]
    )
    tools = {tool.name: tool for tool in build_tools(session, user, object())}
    before = session.query(Question).filter(Question.workbook_id == workbook["id"]).count()

    proposal = tools["generate_questions"].invoke({
        "workbook_id": workbook["id"], "topic": "ReAct",
        "question_type": "true_false", "count": 1, "difficulty": 1,
    })
    assert session.query(Question).filter(Question.workbook_id == workbook["id"]).count() == before

    response = client.post(
        "/api/agent/confirm",
        json={"proposal_id": proposal["proposal_id"], "approved": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["result"]["saved"] == 1
    after = session.query(Question).filter(
        Question.workbook_id == workbook["id"]
    ).count()
    assert after == before + 1


def test_proposal_is_bound_to_its_user(
    client, session, registered_user, auth_headers, workbook
):
    user = _user(session, registered_user)
    node = client.post(
        "/api/knowledge",
        json={"workbook_id": workbook["id"], "name": "私有知识点", "level": 0},
        headers=auth_headers,
    ).json()
    tools = {tool.name: tool for tool in build_tools(session, user, object())}
    proposal = tools["delete_knowledge_node"].invoke({"knowledge_id": node["id"]})
    other = client.post(
        "/api/auth/register",
        json={"username": "other-user", "email": "other@example.com",
              "password": "password123"},
    ).json()

    forbidden = client.post(
        "/api/agent/confirm",
        json={"proposal_id": proposal["proposal_id"], "approved": True},
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    assert forbidden.status_code == 404
    assert session.get(Knowledge, node["id"]) is not None


def test_expired_proposal_is_discarded(
    client, session, monkeypatch, registered_user, auth_headers, workbook
):
    from services import proposal_service

    user = _user(session, registered_user)
    node = client.post(
        "/api/knowledge",
        json={"workbook_id": workbook["id"], "name": "过期知识点", "level": 0},
        headers=auth_headers,
    ).json()
    monkeypatch.setattr(proposal_service, "PROPOSAL_TTL_SEC", 0)
    tools = {tool.name: tool for tool in build_tools(session, user, object())}
    proposal = tools["delete_knowledge_node"].invoke({"knowledge_id": node["id"]})

    response = client.post(
        "/api/agent/confirm",
        json={"proposal_id": proposal["proposal_id"], "approved": True},
        headers=auth_headers,
    )
    assert response.status_code == 410
    assert session.get(Knowledge, node["id"]) is not None
