"""答题记录（不可变审计日志，只增不改）。"""
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, CreatedAtMixin


class AnswerRecord(CreatedAtMixin, Base):
    __tablename__ = "answer_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[str | None] = mapped_column(String(16), nullable=True)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    time_spent: Mapped[int | None] = mapped_column(Integer, nullable=True)
