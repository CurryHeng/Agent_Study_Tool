"""SM-2 间隔重复算法测试（引用真实源码 services/sm2.py，而非复制代码）。"""
from datetime import date, timedelta

from services.sm2 import (
    DEFAULT_EASE,
    MAX_EASE,
    MIN_EASE,
    ReviewCardState,
    create_card_state,
    get_due,
    next_review_label,
    review_card,
)


def test_create_card_state_defaults():
    c = create_card_state()
    assert c.ease == DEFAULT_EASE
    assert c.interval == 0
    assert c.repetitions == 0
    assert c.total_attempts == 0
    assert c.total_correct == 0
    assert c.last_review is None
    assert c.next_review == date.today()


def test_again_resets_repetitions_and_interval():
    c = ReviewCardState(ease=2.5, interval=30, repetitions=3)
    r = review_card(c, "again", is_correct=False, today=date(2025, 6, 1))
    assert r.repetitions == 0
    assert r.interval == 1
    assert r.ease == 2.3  # 2.5 - 0.2
    assert r.total_attempts == 1
    assert r.total_correct == 0


def test_again_ease_not_below_min():
    c = ReviewCardState(ease=MIN_EASE)
    r = review_card(c, "again", is_correct=False)
    assert r.ease == MIN_EASE


def test_first_good_interval_1():
    c = ReviewCardState()
    r = review_card(c, "good", is_correct=True)
    assert r.repetitions == 1
    assert r.interval == 1


def test_second_good_interval_6():
    c = ReviewCardState(repetitions=1, interval=1)
    r = review_card(c, "good", is_correct=True)
    assert r.interval == 6


def test_third_good_interval_ease_multiple():
    c = ReviewCardState(repetitions=2, interval=6, ease=2.5)
    r = review_card(c, "good", is_correct=True, today=date(2025, 6, 1))
    assert r.interval == 15  # 6 * 2.5


def test_easy_interval_and_ease():
    c = ReviewCardState(repetitions=2, interval=6, ease=2.5)
    r = review_card(c, "easy", is_correct=True)
    assert r.interval == 20  # 15 * 1.3 = 19.5 -> 20
    assert r.ease == 2.65  # 2.5 + 0.15


def test_hard_interval_reduced():
    c = ReviewCardState(repetitions=2, interval=6, ease=2.5)
    r = review_card(c, "hard", is_correct=False)
    assert r.interval == 12  # round(15 * 0.8) = 12


def test_ease_capped_at_max():
    c = ReviewCardState(repetitions=2, interval=6, ease=MAX_EASE)
    r = review_card(c, "easy", is_correct=True)
    assert r.ease == MAX_EASE  # 不再无限涨


def test_is_correct_tracking():
    c = ReviewCardState()
    r1 = review_card(c, "good", is_correct=True)
    assert r1.total_attempts == 1
    assert r1.total_correct == 1
    r2 = review_card(r1, "again", is_correct=False)
    assert r2.total_attempts == 2
    assert r2.total_correct == 1


def test_next_review_date():
    c = ReviewCardState(repetitions=2, interval=6, ease=2.5)
    r = review_card(c, "good", is_correct=True, today=date(2025, 6, 1))
    assert r.next_review == date(2025, 6, 1) + timedelta(days=15)


def test_get_due():
    today = date.today()
    due = [
        ReviewCardState(next_review=today - timedelta(days=1)),
        ReviewCardState(next_review=today),
    ]
    not_due = [ReviewCardState(next_review=today + timedelta(days=1))]
    assert len(get_due(due + not_due, today=today)) == 2


def test_next_review_label():
    assert next_review_label(ReviewCardState(interval=0)) == "新题"
    assert next_review_label(ReviewCardState(interval=1)) == "1天"
    assert next_review_label(ReviewCardState(interval=14)) == "2周"
    assert next_review_label(ReviewCardState(interval=30)) == "1月"
