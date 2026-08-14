"""FastAPI 依赖：每个请求一个 Session（P0-2 路由层使用）。"""
from collections.abc import Generator

from sqlalchemy.orm import Session

from db.engine import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
