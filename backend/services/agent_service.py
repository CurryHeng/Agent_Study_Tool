"""Agent 编排入口：运行 ReAct supervisor、提取 steps、记录任务日志。"""
import json
import uuid

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlalchemy.orm import Session

from models import User
from models.enums import AgentTaskStatus
from repositories import agent_task_repository
from workflow.graph import RECURSION_LIMIT, build_graph


def _json_value(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return str(value)


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content or "")


def _tool_summary(name: str, content: str) -> str:
    """把工具 JSON 结果压缩为适合前端展示的摘要。"""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return content[:200]
    if name == "generate_questions" and isinstance(data, dict):
        saved = "已保存" if data.get("saved") else "未保存"
        return f"生成并审核通过 {data.get('approved', 0)} 道题；{saved}"
    if isinstance(data, list):
        return f"返回 {len(data)} 项"
    return json.dumps(data, ensure_ascii=False, default=_json_value)[:200]


def _collect_output(messages: list) -> tuple[str, list[dict], str]:
    calls: dict[str, tuple[str, dict]] = {}
    steps: list[dict] = []
    used_tools: list[str] = []
    reply = ""
    for message in messages:
        if isinstance(message, AIMessage):
            if message.content:
                reply = _content_text(message.content)
            for call in message.tool_calls:
                calls[call["id"]] = (call["name"], call.get("args") or {})
        elif isinstance(message, ToolMessage):
            name, args = calls.get(
                message.tool_call_id, (message.name or "unknown", {})
            )
            content = _content_text(message.content)
            is_error = getattr(message, "status", None) == "error"
            steps.append({
                "tool": name,
                "args": args,
                "ok": not is_error,
                "summary": _tool_summary(name, content),
            })
            used_tools.append(name)
    intent = used_tools[-1] if used_tools else "chat"
    return reply, steps, intent


def run_task(
    db: Session,
    user: User,
    user_request: str,
    workbook_id: int | None = None,
    *,
    graph=None,
) -> dict:
    task_id = str(uuid.uuid4())
    prompt = user_request
    if workbook_id is not None:
        prompt = f"当前练习册 ID：{workbook_id}\n用户请求：{user_request}"
    try:
        runner = graph or build_graph(db, user)
        state = runner.invoke(
            {"messages": [HumanMessage(content=prompt)]},
            config={"recursion_limit": RECURSION_LIMIT},
        )
        reply, steps, intent = _collect_output(state.get("messages", []))
        result = {"reply": reply}
        if steps:
            result["last_tool"] = steps[-1]["tool"]
    except Exception as exc:
        agent_task_repository.create(
            db, user.id, "unknown", input_data=user_request,
            status=AgentTaskStatus.failed, error_message=str(exc)[:500],
        )
        raise

    payload = {
        "task_id": task_id,
        "conversation_id": None,
        "reply": reply,
        "steps": steps,
        "proposals": [],
        "navigate": None,
        "intent": intent,
        "result": result,
    }
    agent_task_repository.create(
        db, user.id, intent, input_data=user_request,
        status=AgentTaskStatus.success,
        result_data=json.dumps(payload, ensure_ascii=False, default=_json_value),
    )
    return payload
