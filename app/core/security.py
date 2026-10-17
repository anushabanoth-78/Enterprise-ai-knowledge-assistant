import datetime as dt
import uuid

import bcrypt
import jwt
import redis
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import repository
from app.db.models import User

log = structlog.get_logger()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
_redis = redis.Redis.from_url(settings.redis_url, socket_timeout=1, socket_connect_timeout=1)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: uuid.UUID) -> str:
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(repository.get_db)
) -> User:
    user = repository.get_user(db, decode_token(token))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def rate_limit(user: User = Depends(get_current_user)) -> User:
    """Fixed-window limiter per user. Fails open if Redis is unavailable."""
    key = f"rl:{user.id}:{int(dt.datetime.now().timestamp() // 60)}"
    try:
        n = _redis.incr(key)
        if n == 1:
            _redis.expire(key, 70)
        if n > settings.rate_limit_per_minute:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
    except redis.RedisError:
        log.warning("rate_limit_redis_unavailable")
    return user
