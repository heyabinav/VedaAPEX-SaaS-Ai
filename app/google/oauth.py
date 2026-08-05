"""Google OAuth 2.0 Authorization Code Flow."""

from utils.time import utcnow

import logging
import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.google.scopes import GOOGLE_AUTH_SCOPES, GOOGLE_AUTH_URL, GOOGLE_TOKEN_URL, GOOGLE_REVOKE_URL

logger = logging.getLogger("google.oauth")

_state_store: Dict[str, int] = {}


def _validate_settings() -> None:
    if not settings.GOOGLE_CLIENT_ID:
        raise ValueError("GOOGLE_CLIENT_ID is not configured")
    if not settings.GOOGLE_CLIENT_SECRET:
        raise ValueError("GOOGLE_CLIENT_SECRET is not configured")


def build_authorization_url(user_id: int) -> tuple[str, str]:
    _validate_settings()
    state = secrets.token_urlsafe(32)
    _state_store[state] = user_id

    params = {
        "response_type": "code",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": " ".join(GOOGLE_AUTH_SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return url, state


def verify_state(state: str) -> Optional[int]:
    user_id = _state_store.pop(state, None)
    if user_id is None:
        logger.warning("Invalid or expired OAuth state")
    return user_id


async def exchange_code(code: str) -> Dict[str, Any]:
    _validate_settings()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data)

    if response.status_code != 200:
        logger.error("Google token exchange failed: %s %s", response.status_code, response.text)
        raise ValueError(f"Google token exchange failed: {response.text}")

    payload = response.json()
    from datetime import datetime, timedelta
    now = utcnow()
    expires_in = payload.get("expires_in")
    expires_at = now + timedelta(seconds=int(expires_in)) if expires_in else None

    return {
        "access_token": payload.get("access_token"),
        "refresh_token": payload.get("refresh_token"),
        "expires_at": expires_at,
        "scope": payload.get("scope"),
        "token_type": payload.get("token_type"),
    }


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    _validate_settings()
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data)

    if response.status_code != 200:
        logger.error("Google token refresh failed: %s %s", response.status_code, response.text)
        raise ValueError(f"Google token refresh failed: {response.text}")

    payload = response.json()
    from datetime import datetime, timedelta
    now = utcnow()
    expires_in = payload.get("expires_in")
    expires_at = now + timedelta(seconds=int(expires_in)) if expires_in else None

    return {
        "access_token": payload.get("access_token"),
        "refresh_token": payload.get("refresh_token", refresh_token),
        "expires_at": expires_at,
        "scope": payload.get("scope"),
        "token_type": payload.get("token_type"),
    }


async def revoke_token(token: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(GOOGLE_REVOKE_URL, params={"token": token})
        return response.status_code == 200
    except Exception as exc:
        logger.error("Token revocation failed: %s", exc)
        return False