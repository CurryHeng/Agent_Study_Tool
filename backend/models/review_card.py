"""SM-2 复习卡（用户对某题的复习状态，复合主键一人一题一卡）。"""
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


class ReviewCard(TimestampMixin, Base):
    __tablename__ = "review_cards"
    __table_args__ = (
        Index("ix_review_cards_user_next", "user_id", "next_review"),
    )

    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    ease: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)
    interval: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_review: Mapped[date] = mapped_column(Date, nullable=False)
    last_review: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    favorited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
