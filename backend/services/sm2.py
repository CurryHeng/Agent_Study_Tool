"""SM-2 间隔重复算法（Python 移植）。

来源：旧项目 `src/lib/sm2.ts` 与 `server/src/lib/sm2.ts`（两处逻辑一致）。
本次移植做了两处修正（详见 P0-1-A 设计报告第 10 节附带决策）：
1. 日期统一使用本地日期（date.today()），修复旧版 toISOString() 的 UTC 偏移 bug。
2. ease 增加上限 MAX_EASE，修复"连续 easy 无限涨"问题。
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

DEFAULT_EASE = 2.5
MIN_EASE = 1.3
MAX_EASE = 4.0
EASE_BONUS = 0.15
EASE_PENALTY = 0.2

Rating = str  # 'again' | 'hard' | 'good' | 'easy'


@dataclass
class ReviewCardState:
    """复习卡的核心调度状态（与数据库字段一一对应）。"""

    ease: float = DEFAULT_EASE
    interval: int = 0
    repetitions: int = 0
    total_attempts: int = 0
    total_correct: int = 0
    next_review: date = field(default_factory=date.today)
    last_review: date | None = None


def create_card_state() -> ReviewCardState:
    """新建复习卡（新题，今天即可复习）。"""
    return ReviewCardState()


def review_card(
    card: ReviewCardState,
    rating: Rating,
    is_correct: bool | None = None,
    today: date | None = None,
) -> ReviewCardState:
    """按评分更新复习卡，返回新的状态（不可变，不修改入参）。"""
    today = today or date.today()
    n = ReviewCardState(
        ease=card.ease,
        interval=card.interval,
        repetitions=card.repetitions,
        total_attempts=card.total_attempts + 1,
        total_correct=card.total_correct + (1 if is_correct else 0),
        last_review=today,
    )

    if rating == "again":
        n.repetitions = 0
        n.interval = 1
        n.ease = max(MIN_EASE, card.ease - EASE_PENALTY)
    else:
        n.repetitions = card.repetitions + 1
        if card.repetitions == 0:
            n.interval = 1
        elif card.repetitions == 1:
            n.interval = 6
        else:
            n.interval = round(card.interval * card.ease)

        if rating == "easy":
            n.interval = round(n.interval * 1.3)
            n.ease = min(MAX_EASE, card.ease + EASE_BONUS)
        elif rating == "hard":
            n.interval = max(round(n.interval * 0.8), 1 if card.interval > 0 else 0)
            n.ease = max(MIN_EASE, card.ease - EASE_PENALTY * 0.5)

    n.next_review = today + timedelta(days=n.interval or 1)
    return n


def get_due(cards: list[ReviewCardState], today: date | None = None) -> list[ReviewCardState]:
    """返回今天及以前到期、需要复习的卡片。"""
    today = today or date.today()
    return [c for c in cards if c.next_review <= today]


def next_review_label(card: ReviewCardState) -> str:
    """下次复习时间的人类可读标签。"""
    if card.interval == 0:
        return "新题"
    if card.interval < 1:
        return "<1天"
    if card.interval == 1:
        return "1天"
    if card.interval < 7:
        return f"{card.interval}天"
    if card.interval < 30:
        return f"{round(card.interval / 7)}周"
    return f"{round(card.interval / 30)}月"
