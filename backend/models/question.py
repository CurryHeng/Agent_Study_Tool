"""题目本身（不含任何用户学习状态）。"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin
from models.enums import QuestionSource, QuestionStatus, QuestionType


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workbook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("knowledge.id", ondelete="SET NULL"), nullable=True, index=True
    )

    type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)  # 唯一正确答案事实源
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # 仅辅助摘要
    image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    source: Mapped[QuestionSource] = mapped_column(
        Enum(QuestionSource), nullable=False, default=QuestionSource.builtin
    )
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus), nullable=False, default=QuestionStatus.approved
    )

    original_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    question_number: Mapped[str | None] = mapped_column(String(64), nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
