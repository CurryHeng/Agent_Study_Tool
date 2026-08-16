"""主 Agent ReAct 图、工具调用轨迹与任务日志测试。"""
import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import ValidationError

from models import AgentTask, User
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
        "tool": "search_documents", "args": {"workbook_id": 3, "query": "ReAct"},
        "ok": True, "summary": "返回 1 项",
    }]
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


def test_generate_step_has_structured_summary(session, registered_user):
    user = _user(session, registered_user)
    messages = [
        AIMessage(content="", tool_calls=[{
            "name": "generate_questions",
            "args": {"workbook_id": 0, "topic": "ReAct", "count": 10},
            "id": "generate", "type": "tool_call",
        }]),
        ToolMessage(
            content='{"preview": [{"content": "题目"}], "approved": 10, "saved": false}',
            tool_call_id="generate",
            name="generate_questions",
        ),
        AIMessage(content="已生成预览。"),
    ]
    result = agent_service.run_task(session, user, "出 10 道题", graph=FakeGraph(messages))
    assert result["steps"][0]["summary"] == "生成并审核通过 10 道题；未保存"


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
            "list_documents", "get_questions", "generate_questions"} <= set(tools)
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
