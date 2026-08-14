"""刷新令牌数据访问层。"""
from datetime import datetime

from sqlalchemy.orm import Session

from models import RefreshToken


def create(db: Session, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(token)
    db.flush()
    return token


def get_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
    return db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()


def delete_by_hash(db: Session, token_hash: str) -> None:
    db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).delete()


def delete_all_for_user(db: Session, user_id: int) -> None:
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
