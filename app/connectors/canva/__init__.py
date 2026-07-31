"""Canva connector."""

from typing import Dict

from app.connectors.base import BaseConnector
from app.connectors.schemas import ConnectorConfig
from app.core.config import settings


class CanvaConnector(BaseConnector):
    _state_store: Dict[str, int] = {}

    @property
    def provider(self) -> str:
        return "canva"

    @property
    def config(self) -> ConnectorConfig:
        scopes_str = settings.CANVA_SCOPES or "openid email profile"
        return ConnectorConfig(
            provider="canva",
            client_id=settings.CANVA_CLIENT_ID or "",
            client_secret=settings.CANVA_CLIENT_SECRET or "",
            redirect_uri=settings.CANVA_REDIRECT_URI or "",
            auth_url=settings.CANVA_AUTHORIZATION_URL,
            token_url=settings.CANVA_TOKEN_URL,
            scopes=scopes_str.split(" "),
            api_base_url=settings.CANVA_API_BASE_URL,
        )

    def build_authorization_url(self, state: str) -> str:
        url = super().build_authorization_url(state)
        self._state_store[state] = True
        return url

    def verify_state(self, state: str) -> bool:
        return self._state_store.pop(state, False) is not False
