"""Token manager - stores, retrieves, and refreshes connector tokens."""

import logging
from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session, select

from app.helpers.token_helper import get_user_token, save_user_token, is_token_valid
from app.connectors.base import BaseConnector
from app.connectors.registry import connector_registry

logger = logging.getLogger("connectors.token_manager")


async def get_valid_access_token(user_id: int, provider: str, session: Session) -> Optional[str]:
    connector = connector_registry.get(provider)
    if not connector:
        return None

    token_data = get_user_token(user_id, provider, session=session)
    if not token_data or not token_data.get("access_token"):
        return None

    if is_token_valid(user_id, provider, session=session):
        return token_data["access_token"]

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        return None

    try:
        refreshed = await connector.refresh_access_token(refresh_token)
        save_user_token(
            user_id, provider,
            refreshed.access_token,
            refreshed.refresh_token or refresh_token,
            refreshed.expires_at,
            session=session,
        )
        logger.info("Refreshed %s token for user_id=%s", provider, user_id)
        return refreshed.access_token
    except (ValueError, Exception) as exc:
        logger.error("Token refresh failed for %s user_id=%s: %s", provider, user_id, exc)
        return None


def store_connector_token(user_id: int, provider: str, tokens, session: Session) -> None:
    save_user_token(
        user_id, provider,
        tokens.access_token,
        tokens.refresh_token,
        tokens.expires_at,
        session=session,
    )
    logger.info("Stored %s token for user_id=%s", provider, user_id)


def get_connector_status(user_id: int, provider: str, session: Session) -> dict:
    token_data = get_user_token(user_id, provider, session=session)
    connected = bool(token_data and token_data.get("access_token"))
    valid = connected and is_token_valid(user_id, provider, session=session)
    return {
        "success": True,
        "provider": provider,
        "connected": connected,
        "valid": valid,
        "expires_at": token_data.get("expires_at") if token_data else None,
        "scopes": token_data.get("scope") if token_data else None,
    }


def disconnect_connector(user_id: int, provider: str, session: Session) -> bool:
    from app.models.user_oauth_tokens import UserOAuthToken
    token_record = session.exec(
        select(UserOAuthToken).where(
            UserOAuthToken.user_id == user_id,
            UserOAuthToken.platform == provider.lower(),
        )
    ).first()
    if not token_record:
        return False
    session.delete(token_record)
    session.commit()
    logger.info("Disconnected %s for user_id=%s", provider, user_id)
    return True
