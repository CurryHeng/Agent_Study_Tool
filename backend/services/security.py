"""密码哈希与 JWT 签发/校验。

参考旧项目 `server/src/lib/jwt.ts` + `server/src/lib/crypto.ts` 的思路：
- access token：HS256，15 分钟
- refresh token：随机 64 字节 hex，数据库只存 sha256 哈希，30 天过期
"""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from config import settings

ACCESS_EXPIRES = timedelta(minutes=15)
REFRESH_EXPIRES = timedelta(days=30)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: int, username: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + ACCESS_EXPIRES,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def generate_refresh_token() -> str:
    return secrets.token_hex(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None) + REFRESH_EXPIRES
