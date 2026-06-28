"""GitHub OAuth provider-specific normalization helper."""

import logging
from typing import Dict, Any

logger = logging.getLogger("auth.github_oauth")


class GithubOAuth:
    @staticmethod
    def normalize(user_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize GitHub user payload from Supabase."""
        user = user_payload or {}
        meta = user.get("user_metadata") or user.get("app_metadata") or {}

        provider = None
        provider_id = None
        identities = user.get("identities") or []
        if identities and isinstance(identities, list) and identities:
            first = identities[0] or {}
            provider = (first.get("provider") or "").lower()
            provider_id = first.get("id") or first.get("user_id") or first.get("sub")

        if not provider:
            provider = "github"
        if not provider_id:
            provider_id = meta.get("github_id") or user.get("id") or user.get("sub")

        full_name = (
            meta.get("full_name") or user.get("name") or meta.get("login") or user.get("login")
        )

        normalized = {
            "id": user.get("id") or user.get("sub") or provider_id,
            "email": user.get("email"),
            "full_name": full_name,
            "provider": provider,
            "provider_id": provider_id,
            "avatar_url": user.get("avatar_url") or meta.get("avatar_url") or user.get("picture"),
        }
        logger.debug(
            "GitHub normalized user: %s",
            {"email": normalized["email"], "provider_id": normalized["provider_id"]},
        )
        return normalized
