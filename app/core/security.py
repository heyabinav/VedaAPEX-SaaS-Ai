from app.utils.time import utcnow

import logging
from datetime import datetime, timedelta
from typing import Any, Union

import bcrypt
from jose import jwt

from app.core.config import settings

logger = logging.getLogger("auth.security")

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = utcnow() + expires_delta
    else:
        expire = utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


# ---------------------------------------------------------------------------
# Password hashing — uses bcrypt directly instead of passlib to avoid the
# known passlib/bcrypt>=4.1 incompatibility that raises:
#   ValueError: password cannot be longer than 72 bytes
# during passlib's internal detect_wrap_bug() check.
# ---------------------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        logger.exception("Password verification failed")
        return False


def get_password_hash(password: str) -> str:
    try:
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        )
        return hashed.decode("utf-8")
    except Exception:
        logger.exception("Password hashing failed")
        raise