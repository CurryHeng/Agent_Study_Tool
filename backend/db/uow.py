"""Unit of Work：统一事务边界（#57）。

用于跨数据库/外部资源操作的场景：先执行预提交回调（如清理 Chroma），
再提交 SQLite 事务；任一步失败都回滚并抛出，避免遗留孤儿数据。
"""
from collections.abc import Callable

from sqlalchemy.orm import Session


class UnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self._pre_commit: list[Callable[[], None]] = []

    def add_pre_commit(self, fn: Callable[[], None]) -> None:
        self._pre_commit.append(fn)

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            self.session.rollback()
            return
        try:
            for fn in self._pre_commit:
                fn()
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
