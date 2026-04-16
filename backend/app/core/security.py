from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(raw: str, hashed: str) -> bool:
    return _pwd.verify(raw, hashed)


def _encode(payload: dict[str, Any], expires: timedelta) -> str:
    s = get_settings()
    to_encode = payload.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires
    return jwt.encode(to_encode, s.app_secret_key, algorithm=s.jwt_algorithm)


def create_access_token(sub: str, extra: dict[str, Any] | None = None) -> str:
    s = get_settings()
    payload: dict[str, Any] = {"sub": sub, "type": "access"}
    if extra:
        payload.update(extra)
    return _encode(payload, timedelta(minutes=s.jwt_access_ttl_min))


def create_refresh_token(sub: str) -> str:
    s = get_settings()
    return _encode({"sub": sub, "type": "refresh"}, timedelta(days=s.jwt_refresh_ttl_days))


def decode_token(token: str) -> dict[str, Any]:
    s = get_settings()
    try:
        return jwt.decode(token, s.app_secret_key, algorithms=[s.jwt_algorithm])
    except JWTError as e:  # pragma: no cover
        raise ValueError("Invalid token") from e
