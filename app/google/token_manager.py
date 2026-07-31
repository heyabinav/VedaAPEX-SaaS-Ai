"""Google token management - store, retrieve, refresh."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlmodel import Session, select

from app.helpers.token_helper import get_user_token, save_user_token, is_token_valid
from app.google.oauth import refresh_access_token

logger = logging.getLogger("google.token_manager")

GOOGLE_PLATFORM = "google"


async def get_valid_token(user_id: int, session: Session) -> Optional[str]:
    token_data = get_user_token(user_id, GOOGLE_PLATFORM, session=session)
    if not token_data or not token_data.get("access_token"):
        return None

    if is_token_valid(user_id, GOOGLE_PLATFORM, session=session):
        return token_data["access_token"]

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        return None

    try:
        refreshed = await refresh_access_token(refresh_token)
        save_user_token(
            user_id,
            GOOGLE_PLATFORM,
            refreshed.get("access_token"),
            refreshed.get("refresh_token", refresh_token),
            refreshed.get("expires_at"),
            session=session,
        )
        logger.info("Refreshed Google token for user_id=%s", user_id)
        return refreshed.get("access_token")
    except ValueError as exc:
        logger.error("Token refresh failed for user_id=%s: %s", user_id, exc)
        return None


def store_token(user_id: int, token_data: dict, session: Session) -> None:
    save_user_token(
        user_id,
        GOOGLE_PLATFORM,
        token_data.get("access_token"),
        token_data.get("refresh_token"),
        token_data.get("expires_at"),
        session=session,
    )
    logger.info("Stored Google token for user_id=%s", user_id)


def get_token_data(user_id: int, session: Session) -> Optional[dict[str, Any]]:
    return get_user_token(user_id, GOOGLE_PLATFORM, session=session)
