from utils.time import utcnow

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("auth.figma")


class FigmaOAuthService:
    @staticmethod
    def _validate_settings() -> None:
        if not settings.FIGMA_CLIENT_ID:
            raise ValueError("FIGMA_CLIENT_ID is not configured")
        if not settings.FIGMA_CLIENT_SECRET:
            raise ValueError("FIGMA_CLIENT_SECRET is not configured")
        if not settings.FIGMA_REDIRECT_URI:
            raise ValueError("FIGMA_REDIRECT_URI is not configured")

    @staticmethod
    def build_authorization_url(state: str) -> str:
        FigmaOAuthService._validate_settings()
        params = {
            "response_type": "code",
            "client_id": settings.FIGMA_CLIENT_ID,
            "redirect_uri": settings.FIGMA_REDIRECT_URI,
            "scope": "file_read file_write offline_access",
            "state": state,
        }
        return f"{settings.FIGMA_AUTHORIZATION_URL}?{httpx.QueryParams(params)}"

    @staticmethod
    async def exchange_code(code: str) -> Dict[str, Any]:
        FigmaOAuthService._validate_settings()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.FIGMA_REDIRECT_URI,
            "client_id": settings.FIGMA_CLIENT_ID,
            "client_secret": settings.FIGMA_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(settings.FIGMA_TOKEN_URL, data=data, headers=headers)

        if response.status_code != 200:
            logger.error("Figma token exchange failed %s %s", response.status_code, response.text)
            raise ValueError(f"Figma token exchange failed: {response.text}")

        payload = response.json()
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

    @staticmethod
    async def refresh_token(refresh_token: str) -> Dict[str, Any]:
        FigmaOAuthService._validate_settings()
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.FIGMA_CLIENT_ID,
            "client_secret": settings.FIGMA_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(settings.FIGMA_TOKEN_URL, data=data, headers=headers)

        if response.status_code != 200:
            logger.error("Figma refresh token failed %s %s", response.status_code, response.text)
            raise ValueError(f"Figma refresh token failed: {response.text}")

        payload = response.json()
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