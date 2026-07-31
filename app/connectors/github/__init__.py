"""GitHub connector."""

from typing import Dict

from app.connectors.base import BaseConnector
from app.connectors.schemas import ConnectorConfig
from app.core.config import settings


class GitHubConnector(BaseConnector):
    _state_store: Dict[str, int] = {}

    @property
    def provider(self) -> str:
        return "github"

    @property
    def config(self) -> ConnectorConfig:
        return ConnectorConfig(
            provider="github",
            client_id=settings.GITHUB_CLIENT_ID or "",
            client_secret=settings.GITHUB_CLIENT_SECRET or "",
            redirect_uri=settings.GITHUB_REDIRECT_URI or "",
            auth_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=[
                "repo", "read:user", "user:email",
                "read:org", "read:repo_hook", "read:discussion",
            ],
        )

    def build_authorization_url(self, state: str) -> str:
        url = super().build_authorization_url(state)
        self._state_store[state] = True
        return url

    def verify_state(self, state: str) -> bool:
        return self._state_store.pop(state, False) is not False

    def _auth_headers(self, access_token: str) -> dict:
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
