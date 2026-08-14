"""Agent 任务（P0-8 使用，用于调试 Agent 执行链）。"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, utcnow
from models.enums import AgentTaskStatus


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[AgentTaskStatus] = mapped_column(
        Enum(AgentTaskStatus), nullable=False, default=AgentTaskStatus.pending
    )
    input_data: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON 字符串
    result_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 字符串
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
