"""FSRS-6 间隔重复调度（py-fsrs 封装）。

替代旧 SM-2（services/sm2.py 已删除）：
- 评分沿用四档：again / hard / good / easy（与 SM-2 一致，前端无需改评分交互）
- 卡状态由 ease/interval/repetitions 升级为 FSRS 的 state/step/stability/difficulty
- due 为分钟级（学习步长 1min/10min），数据库统一存 naive UTC，读出时补回 tzinfo
"""
from datetime import UTC, datetime

from fsrs import Card, Rating, Scheduler, State

_scheduler = Scheduler()  # FSRS-6 默认 21 参数，desired_retention=0.9

RATING_MAP = {
    "again": Rating.Again,
    "hard": Rating.Hard,
    "good": Rating.Good,
    "easy": Rating.Easy,
}

DEFAULT_STATE = State.Learning.name


def _to_fsrs_card(row) -> Card:
    """DB 行 → fsrs.Card（naive UTC 补回 tzinfo）。"""
    due = row.due.replace(tzinfo=UTC) if row.due else None
    last = row.last_review.replace(tzinfo=UTC) if row.last_review else None
    return Card(
        card_id=row.question_id,
        state=State[row.state] if row.state else State.Learning,
        step=row.step,
        stability=row.stability,
        difficulty=row.difficulty,
        due=due,
        last_review=last,
    )


def apply_review(row, rating: str) -> None:
    """按评分更新 DB 行的 FSRS 状态（原地修改，调用方负责 flush）。

    total_attempts / total_correct 由业务层维护，不在此处处理。
    """
    card = _to_fsrs_card(row)
    new_card, _log = _scheduler.review_card(card, RATING_MAP[rating])
    row.state = new_card.state.name
    row.step = new_card.step
    row.stability = new_card.stability
    row.difficulty = new_card.difficulty
    row.due = new_card.due.replace(tzinfo=None) if new_card.due else None
    row.last_review = (
        new_card.last_review.replace(tzinfo=None) if new_card.last_review else None
    )


def is_due(row, now: datetime | None = None) -> bool:
    """卡片是否到期（naive UTC 比较）。"""
    now = now or datetime.now(UTC).replace(tzinfo=None)
    return row.due is not None and row.due <= now


def due_label(due: datetime | None, now: datetime | None = None) -> str:
    """下次复习时间的人类可读标签（支持分钟级）。"""
    if due is None:
        return "新题"
    now = now or datetime.now(UTC).replace(tzinfo=None)
    seconds = (due - now).total_seconds()
    if seconds <= 0:
        return "现在"
    if seconds < 3600:
        return f"{max(1, round(seconds / 60))}分钟后"
    if seconds < 86400:
        return f"{round(seconds / 3600)}小时后"
    days = round(seconds / 86400)
    if days < 7:
        return f"{days}天后"
    if days < 30:
        return f"{round(days / 7)}周后"
    return f"{round(days / 30)}月后"
