"""SQLAlchemy 声明式基类与通用 Mixin。"""
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """统一的 UTC 时间戳（SQLite 存 naive UTC，避免时区比较报错）。"""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """所有模型的公共基类，也是 Alembic 迁移的唯一 metadata 来源。"""


class TimestampMixin:
    """created_at + updated_at（会随记录变化的核心业务表用）。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class CreatedAtMixin:
    """仅 created_at（只增不改的审计日志表用）。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
