"""Notion connector."""

from typing import Dict

from app.connectors.base import BaseConnector
from app.connectors.schemas import ConnectorConfig
from app.core.config import settings


class NotionConnector(BaseConnector):
    _state_store: Dict[str, int] = {}

    @property
    def provider(self) -> str:
        return "notion"

    @property
    def config(self) -> ConnectorConfig:
        return ConnectorConfig(
            provider="notion",
            client_id=settings.NOTION_CLIENT_ID or "",
            client_secret=settings.NOTION_CLIENT_SECRET or "",
            redirect_uri=settings.NOTION_REDIRECT_URI or "",
            auth_url="https://api.notion.com/v1/oauth/authorize",
            token_url="https://api.notion.com/v1/oauth/token",
            scopes=[],
            api_base_url="https://api.notion.com/v1",
            extra_params={"owner": "user", "response_type": "code"},
        )

    def build_authorization_url(self, state: str) -> str:
        from urllib.parse import urlencode
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "owner": "user",
            "state": state,
        }
        url = f"{self.config.auth_url}?{urlencode(params)}"
        self._state_store[state] = True
        return url

    async def exchange_code(self, code: str):
        import httpx
        import base64
        credentials = base64.b64encode(
            f"{self.config.client_id}:{self.config.client_secret}".encode()
        ).decode()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.config.token_url,
                data={"grant_type": "authorization_code", "code": code, "redirect_uri": self.config.redirect_uri},
                headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
            )
        if response.status_code != 200:
            raise ValueError(f"Notion token exchange failed: {response.text}")
        return self._parse_token_response(response.json())

    async def refresh_access_token(self, refresh_token: str):
        raise ValueError("Notion does not support refresh tokens - user must re-authorize")

    def verify_state(self, state: str) -> bool:
        return self._state_store.pop(state, False) is not False

    def _auth_headers(self, access_token: str) -> dict:
        return {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
