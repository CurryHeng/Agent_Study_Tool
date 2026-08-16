"""学习活动时间线 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel


class HistoryEventOut(BaseModel):
    id: str
    type: str
    title: str
    detail: str | None = None
    created_at: datetime
