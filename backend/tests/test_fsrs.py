"""FSRS-6 调度封装测试（services/fsrs_scheduler.py）。"""
from datetime import UTC, datetime, timedelta

from models import ReviewCard
from services.fsrs_scheduler import apply_review, due_label, is_due


def _card(question_id=1) -> ReviewCard:
    """构造一张新复习卡（内存对象，不落库）。"""
    return ReviewCard(
        question_id=question_id,
        user_id=1,
        state="Learning",
        step=None,
        stability=None,
        difficulty=None,
        due=datetime.now(UTC).replace(tzinfo=None),
        last_review=None,
    )


def test_new_card_first_good_enters_learning_with_stability():
    card = _card()
    apply_review(card, "good")
    assert card.state in ("Learning", "Review")
    assert card.stability is not None and card.stability > 0
    assert card.difficulty is not None
    assert card.last_review is not None


def test_again_after_review_resets_to_relearning_or_learning():
    card = _card()
    for _ in range(5):  # 连续答对，推进到 Review 态
        card.due = datetime.now(UTC).replace(tzinfo=None)
        apply_review(card, "good")
    assert card.state == "Review"
    stability_before = card.stability

    card.due = datetime.now(UTC).replace(tzinfo=None)
    apply_review(card, "again")
    assert card.state in ("Relearning", "Learning")
    assert card.stability < stability_before  # 遗忘后稳定度下降


def test_good_streak_extends_due():
    card = _card()
    dues = []
    for _ in range(4):
        card.due = datetime.now(UTC).replace(tzinfo=None)
        apply_review(card, "good")
        dues.append(card.due)
    # 连续答对，到期时间应当单调后移
    assert dues == sorted(dues)
    assert dues[-1] > datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)


def test_easy_rates_farther_than_hard():
    def run(rating):
        card = _card()
        card.due = datetime.now(UTC).replace(tzinfo=None)
        apply_review(card, rating)
        card.due = datetime.now(UTC).replace(tzinfo=None)
        apply_review(card, rating)
        return card.due

    assert run("easy") > run("hard")


def test_is_due_and_label():
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
    future_min = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=30)
    future_day = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=3)

    card = _card()
    card.due = past
    assert is_due(card) is True
    card.due = future_min
    assert is_due(card) is False

    assert due_label(past) == "现在"
    assert "分钟" in due_label(future_min)
    assert "天" in due_label(future_day)
    assert due_label(None) == "新题"


def test_unknown_rating_raises():
    import pytest

    card = _card()
    with pytest.raises(KeyError):
        apply_review(card, "perfect")
