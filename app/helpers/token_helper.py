import base64
import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

from cryptography.fernet import Fernet
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.user_oauth_tokens import UserOAuthToken

logger = logging.getLogger("auth.token_helper")

def _build_cipher() -> Fernet:
    raw_key = os.getenv("OAUTH_TOKEN_ENCRYPTION_KEY") or os.getenv("FERNET_KEY")
    if not raw_key:
        raw_key = Fernet.generate_key().decode("utf-8")
        os.environ["OAUTH_TOKEN_ENCRYPTION_KEY"] = raw_key

    try:
        return Fernet(raw_key.encode("utf-8"))
    except ValueError:
        derived_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode("utf-8")).digest()).decode("utf-8")
        os.environ["OAUTH_TOKEN_ENCRYPTION_KEY"] = derived_key
        return Fernet(derived_key.encode("utf-8"))


_cipher = _build_cipher()


def _encrypt_text(value: str) -> str:
    return _cipher.encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt_text(value: str) -> str:
    return _cipher.decrypt(value.encode("utf-8")).decode("utf-8")


def save_user_token(
    user_id: int,
    platform: str,
    access_token: Optional[str],
    refresh_token: Optional[str],
    expires_at: Optional[datetime] = None,
    session: Optional[Session] = None,
) -> UserOAuthToken:
    if session is None:
        with next(get_session()) as db_session:
            return save_user_token(
                user_id,
                platform,
                access_token,
                refresh_token,
                expires_at,
                session=db_session,
            )

    token_record = session.exec(
        select(UserOAuthToken).where(
            UserOAuthToken.user_id == user_id,
            UserOAuthToken.platform == platform.lower(),
        )
    ).first()

    if token_record is None:
        token_record = UserOAuthToken(user_id=user_id, platform=platform.lower())
        session.add(token_record)

    token_record.access_token = _encrypt_text(access_token or "")
    token_record.refresh_token = _encrypt_text(refresh_token or "")
    token_record.expires_at = expires_at
    session.commit()
    session.refresh(token_record)
    return token_record


def get_user_token(
    user_id: int,
    platform: str,
    session: Optional[Session] = None,
) -> Optional[dict[str, Any]]:
    if session is None:
        with next(get_session()) as db_session:
            return get_user_token(user_id, platform, session=db_session)

    token_record = session.exec(
        select(UserOAuthToken).where(
            UserOAuthToken.user_id == user_id,
            UserOAuthToken.platform == platform.lower(),
        )
    ).first()

    if not token_record:
        return None

    return {
        "id": token_record.id,
        "user_id": token_record.user_id,
        "platform": token_record.platform,
        "access_token": _decrypt_text(token_record.access_token) if token_record.access_token else "",
        "refresh_token": _decrypt_text(token_record.refresh_token) if token_record.refresh_token else "",
        "expires_at": token_record.expires_at,
        "created_at": token_record.created_at,
    }


def refresh_token_if_expired(
    user_id: int,
    platform: str,
    refresh_callback: Optional[Any] = None,
    session: Optional[Session] = None,
) -> Optional[dict[str, Any]]:
    token_data = get_user_token(user_id, platform, session=session)
    if not token_data:
        return None

    if not is_token_valid(user_id, platform, session=session):
        if not refresh_callback:
            return token_data
        refreshed = refresh_callback(token_data["refresh_token"])
        if not refreshed:
            return token_data
        return save_user_token(
            user_id,
            platform,
            refreshed.get("access_token"),
            refreshed.get("refresh_token"),
            refreshed.get("expires_at"),
            session=session,
        )

    return token_data


def is_token_valid(
    user_id: int,
    platform: str,
    session: Optional[Session] = None,
) -> bool:
    token_data = get_user_token(user_id, platform, session=session)
    if not token_data:
        return False

    expires_at = token_data.get("expires_at")
    if not expires_at:
        return bool(token_data.get("access_token"))

    return datetime.utcnow() < expires_at - timedelta(minutes=5)
