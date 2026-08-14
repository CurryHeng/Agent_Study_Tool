"""数据库引擎与 Session 工厂。

引擎是唯一的连接工厂；SQLite 下强制开启外键约束（PRAGMA foreign_keys=ON），
否则 CASCADE / RESTRICT / SET NULL 不会生效（这正是 P0-0 审计发现的隐患）。
"""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from config import settings


def _enable_sqlite_fk(dbapi_conn, _record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_app_engine(url: str | None = None) -> Engine:
    """创建引擎；SQLite 额外设置 check_same_thread=False 与外键 pragma。"""
    url = url or settings.database_url
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_fk)
    return engine


engine = create_app_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
