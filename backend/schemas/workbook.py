"""练习册 Pydantic 请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkbookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class WorkbookUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class WorkbookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
