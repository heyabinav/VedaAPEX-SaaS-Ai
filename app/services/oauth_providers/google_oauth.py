"""Google OAuth provider-specific normalization helper."""

import logging
from typing import Dict, Any

logger = logging.getLogger("auth.google_oauth")


class GoogleOAuth:
    @staticmethod
    def normalize(user_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Google user payload from Supabase."""
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
            provider = "google"
        if not provider_id:
            provider_id = user.get("sub") or user.get("id")

        normalized = {
            "id": user.get("id") or user.get("sub") or provider_id,
            "email": user.get("email"),
            "full_name": meta.get("full_name") or meta.get("name") or user.get("name"),
            "provider": provider,
            "provider_id": provider_id,
            "avatar_url": user.get("picture") or meta.get("avatar_url") or user.get("avatar_url"),
        }
        logger.debug(
            "Google normalized user: %s",
            {"email": normalized["email"], "provider_id": normalized["provider_id"]},
        )
        return normalized
