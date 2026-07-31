"""Google Workspace connector."""

import secrets
from typing import Dict

from app.connectors.base import BaseConnector
from app.connectors.schemas import ConnectorConfig
from app.core.config import settings


class GoogleConnector(BaseConnector):
    _state_store: Dict[str, int] = {}

    @property
    def provider(self) -> str:
        return "google"

    @property
    def config(self) -> ConnectorConfig:
        return ConnectorConfig(
            provider="google",
            client_id=settings.GOOGLE_CLIENT_ID or "",
            client_secret=settings.GOOGLE_CLIENT_SECRET or "",
            redirect_uri=settings.GOOGLE_REDIRECT_URI or "",
            auth_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[
                "openid", "email", "profile",
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/presentations",
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/contacts.readonly",
            ],
            extra_params={"access_type": "offline", "prompt": "consent"},
        )

    def build_authorization_url(self, state: str) -> str:
        url = super().build_authorization_url(state)
        self._state_store[state] = True
        return url

    def verify_state(self, state: str) -> bool:
        return self._state_store.pop(state, False) is not False

    async def revoke_token(self, token: str) -> bool:
        try:
            await self._get("https://oauth2.googleapis.com/revoke", token, params={"token": token})
            return True
        except Exception:
            return False
