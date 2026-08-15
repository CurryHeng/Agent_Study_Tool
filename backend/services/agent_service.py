"""Agent 编排入口：构建 LangGraph、执行任务、记录 AgentTask 日志。"""
import json
import uuid

from sqlalchemy.orm import Session

from models import User
from models.enums import AgentTaskStatus
from repositories import agent_task_repository
from workflow.graph import build_graph
from workflow.state import TaskState


def run_task(
    db: Session,
    user: User,
    user_request: str,
    workbook_id: int | None = None,
    navigator_llm=None,
    generate_fn=None,
    review_fn=None,
    save_fn=None,
) -> dict:
    graph = build_graph(
        db,
        user,
        navigator_llm=navigator_llm,
        generate_fn=generate_fn,
        review_fn=review_fn,
        save_fn=save_fn,
        workbook_hint=workbook_id,
    )
    task_id = str(uuid.uuid4())
    initial: TaskState = {
        "task_id": task_id,
        "user_id": user.id,
        "workbook_id": workbook_id,
        "user_request": user_request,
        "retry_count": 0,
        "errors": [],
    }
    try:
        result = graph.invoke(initial)
    except Exception as exc:
        agent_task_repository.create(
            db,
            user.id,
            "unknown",
            input_data=user_request,
            status=AgentTaskStatus.failed,
            error_message=str(exc)[:500],
        )
        raise

    intent = result.get("intent") or "chat"
    errors = result.get("errors") or []
    status = AgentTaskStatus.failed if errors else AgentTaskStatus.success

    def _dump_fallback(obj):
        """AgentTask.result_data 统一存 JSON 字符串（Pydantic 模型/datetime/枚举等均可序列化）。"""
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "value"):  # 枚举
            return obj.value
        return str(obj)

    agent_task_repository.create(
        db,
        user.id,
        intent,
        input_data=user_request,
        status=status,
        result_data=json.dumps(
            result.get("final_result") or {}, ensure_ascii=False, default=_dump_fallback
        ),
        error_message="; ".join(str(e) for e in errors)[:500] or None,
    )

    return {
        "task_id": task_id,
        "intent": intent,
        "result": result.get("final_result") or {},
    }
