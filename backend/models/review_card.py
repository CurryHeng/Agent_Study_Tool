"""FSRS 复习卡（用户对某题的复习状态，复合主键一人一题一卡）。

SM-2 → FSRS-6 迁移（2026-08-15）：
ease/interval/repetitions/next_review 废弃，
改为 state/step/stability/difficulty + due（DateTime，naive UTC）。
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


class ReviewCard(TimestampMixin, Base):
    __tablename__ = "review_cards"
    __table_args__ = (
        Index("ix_review_cards_user_due", "user_id", "due"),
    )

    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    # ── FSRS-6 调度状态 ──
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="Learning")
    step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    due: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_review: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── 业务统计（与调度算法无关，保留）──
    total_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    favorited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
