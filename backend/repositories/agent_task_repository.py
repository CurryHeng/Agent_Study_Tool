"""Agent 任务数据访问层（详细设计 Pt.3 §17 日志/调试）。"""
from sqlalchemy.orm import Session

from models import AgentTask
from models.enums import AgentTaskStatus


def create(
    db: Session,
    user_id: int,
    task_type: str,
    input_data: str | None,
    status: AgentTaskStatus = AgentTaskStatus.pending,
    result_data: str | None = None,
    error_message: str | None = None,
) -> AgentTask:
    task = AgentTask(
        user_id=user_id,
        task_type=task_type,
        status=status,
        input_data=input_data,
        result_data=result_data,
        error_message=error_message,
    )
    db.add(task)
    db.flush()
    return task
