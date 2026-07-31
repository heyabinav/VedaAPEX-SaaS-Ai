"""Build authenticated httpx clients for Google API calls."""

import logging
from typing import Optional

import httpx

from app.google.token_manager import get_valid_token

logger = logging.getLogger("google.credentials")


async def get_auth_headers(user_id: int, session) -> Optional[dict]:
    access_token = await get_valid_token(user_id, session)
    if not access_token:
        return None
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


async def google_api_call(
    user_id: int,
    session,
    method: str,
    url: str,
    json_data: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: float = 30.0,
) -> dict:
    headers = await get_auth_headers(user_id, session)
    if not headers:
        raise ValueError("Google account not connected or token expired")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            params=params,
        )

    if response.status_code == 401:
        raise ValueError("Google token expired or revoked - please reconnect")
    if response.status_code == 403:
        raise ValueError("Insufficient Google API permissions - check scopes")
    if response.status_code == 429:
        raise ValueError("Google API rate limit exceeded - try again later")
    if response.status_code >= 400:
        raise ValueError(f"Google API error {response.status_code}: {response.text}")

    if response.status_code == 204:
        return {}
    return response.json()
