"""用户数据访问层。"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_by_email_or_username(db: Session, email: str, username: str) -> User | None:
    return (
        db.query(User)
        .filter(or_(User.email == email, User.username == username))
        .first()
    )


def create(db: Session, username: str, email: str, password_hash: str) -> User:
    user = User(username=username, email=email, password_hash=password_hash)
    db.add(user)
    db.flush()
    return user
