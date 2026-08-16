"""知识点语义关联（#58）。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, CreatedAtMixin, utcnow


class KnowledgeRelation(CreatedAtMixin, Base):
    __tablename__ = "knowledge_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workbook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_knowledge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_knowledge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
