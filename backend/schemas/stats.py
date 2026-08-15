"""学习统计聚合 Pydantic 模型。"""
from pydantic import BaseModel


class BucketOut(BaseModel):
    label: str
    count: int


class HeatmapItemOut(BaseModel):
    knowledge_id: int | None = None
    name: str
    total: int
    errors: int


class ActivityDayOut(BaseModel):
    date: str
    total: int
    correct: int


class ReasonOut(BaseModel):
    name: str
    count: int


class RecentOut(BaseModel):
    date: str
    rating: str | None
    mode: str | None
    is_correct: int | None
    question_id: int
    question_content: str


class StatsOut(BaseModel):
    cards_total: int
    cards_due: int
    reviewed_today: int
    favorites: int
    question_total: int
    mastery: dict[str, int]
    accuracy_buckets: list[BucketOut]
    knowledge_heatmap: list[HeatmapItemOut]
    activity_heatmap: list[ActivityDayOut]
    wrong_reasons: list[ReasonOut]
    recent: list[RecentOut]
    week_minutes: int
    week_days: int
