"""文档（P0-4 文档解析使用，P0-1 先建表）。"""
import os

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, CreatedAtMixin
from models.enums import DocumentStatus


class Document(CreatedAtMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workbook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), nullable=False, default=DocumentStatus.pending
    )

    @property
    def file_size(self) -> int:
        """已上传文件的字节数（只读，从磁盘读取，无需入库）。"""
        try:
            return os.path.getsize(self.file_path)
        except OSError:
            return 0

