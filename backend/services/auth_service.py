"""认证业务逻辑（register / login / refresh / logout）。"""
from sqlalchemy.orm import Session

from db.base import utcnow
from models import User
from repositories import refresh_token_repository, user_repository
from services import security


class AuthError(Exception):
    """认证业务异常，携带 HTTP 状态码。"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def _issue_tokens(db: Session, user: User) -> tuple[str, str]:
    """签发 access + refresh，并把 refresh 哈希落库。"""
    access = security.create_access_token(user.id, user.username)
    refresh = security.generate_refresh_token()
    refresh_token_repository.create(
        db, user.id, security.hash_refresh_token(refresh), security.refresh_token_expiry()
    )
    return access, refresh


def register(db: Session, username: str, email: str, password: str) -> tuple[User, str, str]:
    if user_repository.get_by_email_or_username(db, email, username):
        raise AuthError(409, "用户名或邮箱已被注册")
    user = user_repository.create(db, username, email, security.hash_password(password))
    access, refresh = _issue_tokens(db, user)
    return user, access, refresh


def login(db: Session, email: str, password: str) -> tuple[User, str, str]:
    user = user_repository.get_by_email(db, email)
    if user is None or not security.verify_password(password, user.password_hash):
        raise AuthError(401, "邮箱或密码错误")
    access, refresh = _issue_tokens(db, user)
    return user, access, refresh


def refresh(db: Session, refresh_token: str) -> tuple[User, str, str]:
    token_hash = security.hash_refresh_token(refresh_token)
    row = refresh_token_repository.get_by_hash(db, token_hash)
    if row is None:
        raise AuthError(401, "无效的 refresh token")
    if row.expires_at < utcnow():
        refresh_token_repository.delete_by_hash(db, token_hash)
        raise AuthError(401, "refresh token 已过期，请重新登录")

    user = user_repository.get_by_id(db, row.user_id)
    if user is None:
        raise AuthError(401, "用户不存在")

    # 轮换：旧 refresh 作废，签发新令牌
    refresh_token_repository.delete_by_hash(db, token_hash)
    access, new_refresh = _issue_tokens(db, user)
    return user, access, new_refresh


def logout(db: Session, user_id: int, refresh_token: str) -> None:
    token_hash = security.hash_refresh_token(refresh_token)
    row = refresh_token_repository.get_by_hash(db, token_hash)
    if row is not None and row.user_id == user_id:
        refresh_token_repository.delete_by_hash(db, token_hash)
