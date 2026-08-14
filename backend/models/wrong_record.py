"""错题本条目（用户主观错因反思，可编辑）。"""
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, CreatedAtMixin


class WrongRecord(CreatedAtMixin, Base):
    __tablename__ = "wrong_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    wrong_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    wrong_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
