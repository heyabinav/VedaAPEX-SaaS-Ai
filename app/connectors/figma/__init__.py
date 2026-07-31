"""Figma connector."""

from typing import Dict

from app.connectors.base import BaseConnector
from app.connectors.schemas import ConnectorConfig
from app.core.config import settings


class FigmaConnector(BaseConnector):
    _state_store: Dict[str, int] = {}

    @property
    def provider(self) -> str:
        return "figma"

    @property
    def config(self) -> ConnectorConfig:
        return ConnectorConfig(
            provider="figma",
            client_id=settings.FIGMA_CLIENT_ID or "",
            client_secret=settings.FIGMA_CLIENT_SECRET or "",
            redirect_uri=settings.FIGMA_REDIRECT_URI or "",
            auth_url=settings.FIGMA_AUTHORIZATION_URL,
            token_url=settings.FIGMA_TOKEN_URL,
            scopes=["file_read", "file_write", "offline_access"],
            api_base_url=settings.FIGMA_API_BASE_URL,
        )

    def build_authorization_url(self, state: str) -> str:
        url = super().build_authorization_url(state)
        self._state_store[state] = True
        return url

    def verify_state(self, state: str) -> bool:
        return self._state_store.pop(state, False) is not False

    def _auth_headers(self, access_token: str) -> dict:
        return {"X-Figma-Token": access_token, "Accept": "application/json"}
