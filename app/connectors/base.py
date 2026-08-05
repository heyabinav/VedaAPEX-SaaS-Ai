"""Base connector class - all providers extend this."""

from utils.time import utcnow

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.connectors.schemas import ConnectorConfig, OAuthTokens

logger = logging.getLogger("connectors.base")


class BaseConnector(ABC):
    """Abstract base class for all OAuth connectors."""

    @property
    @abstractmethod
    def provider(self) -> str:
        ...

    @property
    @abstractmethod
    def config(self) -> ConnectorConfig:
        ...

    def build_authorization_url(self, state: str) -> str:
        from urllib.parse import urlencode
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "state": state,
        }
        if self.config.scopes:
            if self.provider == "notion":
                params["owner"] = "user"
            else:
                params["scope"] = " ".join(self.config.scopes)
        params.update(self.config.extra_params)
        return f"{self.config.auth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
        payload = await self._post(self.config.token_url, data=data, headers=headers)
        return self._parse_token_response(payload)

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
        payload = await self._post(self.config.token_url, data=data, headers=headers)
        tokens = self._parse_token_response(payload)
        if not tokens.refresh_token:
            tokens.refresh_token = refresh_token
        return tokens

    async def revoke_token(self, token: str) -> bool:
        return True

    def _parse_token_response(self, payload: dict) -> OAuthTokens:
        now = utcnow()
        expires_in = payload.get("expires_in")
        expires_at = now + timedelta(seconds=int(expires_in)) if expires_in else None
        return OAuthTokens(
            access_token=payload.get("access_token", ""),
            refresh_token=payload.get("refresh_token"),
            expires_at=expires_at,
            scope=payload.get("scope"),
            token_type=payload.get("token_type"),
        )

    async def _post(self, url: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, **kwargs)
        if response.status_code != 200:
            logger.error("%s request failed: %s %s", self.provider, response.status_code, response.text)
            raise ValueError(f"{self.provider.title()} token exchange failed: {response.text}")
        return response.json()

    async def _get(self, url: str, access_token: str, params: Optional[dict] = None, timeout: float = 30.0) -> dict:
        headers = self._auth_headers(access_token)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers, params=params)
        if response.status_code == 401:
            raise ValueError(f"{self.provider.title()} token expired or revoked")
        if response.status_code == 403:
            raise ValueError(f"Insufficient {self.provider.title()} permissions")
        if response.status_code == 429:
            raise ValueError(f"{self.provider.title()} rate limit exceeded")
        if response.status_code >= 400:
            raise ValueError(f"{self.provider.title()} API error {response.status_code}: {response.text}")
        if response.status_code == 204:
            return {}
        return response.json()

    def _auth_headers(self, access_token: str) -> dict:
        return {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}