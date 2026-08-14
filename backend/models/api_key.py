"""用户 API Key（加密存储）。"""
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    deepseek_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    qwen_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
