"""
Supabase OAuth helper — performs server-side token exchange and provider-specific normalization.

This file is created by the integration patch to support Google and GitHub provider normalization
and secure server-side code->token exchange with Supabase.
"""

import base64
import logging
from typing import Dict, Any, Optional

import httpx
import os
import importlib

from app.core.config import settings

logger = logging.getLogger("auth.supabase_oauth")


class SupabaseOAuthError(Exception):
    pass


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    creds = f"{client_id}:{client_secret}"
    b64 = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
    return f"Basic {b64}"


async def exchange_code_for_token(
    code: str, redirect_uri: str, provider: Optional[str] = None, timeout: int = 15
) -> Dict[str, Any]:
    supabase_base = (os.getenv("SUPABASE_URL") or settings.SUPABASE_URL or "").rstrip("/")
    if not supabase_base:
        raise SupabaseOAuthError("SUPABASE_URL not configured")

    token_url = f"{supabase_base}/auth/v1/token"

    # Get provider-specific credentials
    client_id = None
    client_secret = None

    if provider and provider.lower() == "google":
        client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID") or settings.GOOGLE_OAUTH_CLIENT_ID
        client_secret = (
            os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or settings.GOOGLE_OAUTH_CLIENT_SECRET
        )
        logger.debug("Using Google OAuth credentials")
    elif provider and provider.lower() == "github":
        client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID") or settings.GITHUB_OAUTH_CLIENT_ID
        client_secret = (
            os.getenv("GITHUB_OAUTH_CLIENT_SECRET") or settings.GITHUB_OAUTH_CLIENT_SECRET
        )
        logger.debug("Using GitHub OAuth credentials")
    else:
        # Fallback to generic credentials if provider not detected
        client_id = os.getenv("OAUTH_CLIENT_ID") or settings.OAUTH_CLIENT_ID
        client_secret = os.getenv("OAUTH_CLIENT_SECRET") or settings.OAUTH_CLIENT_SECRET
        logger.debug("Using generic OAuth credentials (provider=%s)", provider)

    if not client_id or not client_secret:
        raise SupabaseOAuthError(f"OAuth credentials not configured for provider={provider}")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Authorization": _basic_auth_header(client_id, client_secret),
        "apikey": os.getenv("SUPABASE_ANON_KEY") or settings.SUPABASE_KEY or "",
    }

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    logger.debug("Exchanging code for token at %s", token_url)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(token_url, headers=headers, data=data)
    except httpx.HTTPError as exc:
        logger.exception("HTTP error while exchanging code: %s", exc)
        raise SupabaseOAuthError("Failed to reach Supabase token endpoint") from exc

    try:
        payload = resp.json()
    except Exception:
        payload = {"message": resp.text}

    logger.debug("Token endpoint returned status=%s payload=%s", resp.status_code, payload)

    if resp.status_code not in (200, 201):
        msg = payload.get("error") or payload.get("message") or str(payload)
        raise SupabaseOAuthError(f"Token exchange failed: {msg}")

    return payload


def detect_provider_from_payload(payload: Dict[str, Any]) -> Optional[str]:
    try:
        if isinstance(payload, dict):
            if payload.get("provider"):
                return payload.get("provider")
            user = payload.get("user") or {}
            identities = user.get("identities") or []
            if identities and isinstance(identities, list) and identities:
                first = identities[0] or {}
                p = first.get("provider")
                if p:
                    return p.lower()
            app_md = user.get("app_metadata") or {}
            if isinstance(app_md, dict):
                if app_md.get("provider"):
                    return str(app_md.get("provider")).lower()
            if user.get("aud") and "google" in user.get("aud", ""):
                return "google"
    except Exception:
        logger.debug("Provider detection failed for payload", exc_info=True)
    return None


async def fetch_user_from_access_token(access_token: str, timeout: int = 15) -> Dict[str, Any]:
    supabase_base = (os.getenv("SUPABASE_URL") or settings.SUPABASE_URL or "").rstrip("/")
    if not supabase_base:
        raise SupabaseOAuthError("SUPABASE_URL not configured")

    url = f"{supabase_base}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "apikey": os.getenv("SUPABASE_ANON_KEY") or settings.SUPABASE_KEY or "",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        logger.exception("HTTP error while fetching user info: %s", exc)
        raise SupabaseOAuthError("Failed to reach Supabase user endpoint") from exc

    try:
        data = resp.json()
    except Exception:
        data = {"message": resp.text}

    if resp.status_code != 200:
        msg = data.get("error") or data.get("message") or str(data)
        raise SupabaseOAuthError(f"Failed to get user info: {msg}")

    return data


def _load_provider_module(provider: str):
    if not provider:
        return None
    mapping = {
        "google": ("app.services.oauth_providers.google_oauth", "GoogleOAuth"),
        "github": ("app.services.oauth_providers.github_oauth", "GithubOAuth"),
    }
    info = mapping.get(provider.lower())
    if not info:
        return None
    module_name, class_name = info
    try:
        module = importlib.import_module(module_name)
        klass = getattr(module, class_name)
        return klass
    except Exception:
        logger.exception("Failed to load provider module for %s", provider)
        return None


def normalize_supabase_user(
    user_payload: Dict[str, Any], provider: Optional[str] = None
) -> Dict[str, Any]:
    provider_cls = _load_provider_module(provider) if provider else None
    if provider_cls:
        try:
            return provider_cls.normalize(user_payload)
        except Exception:
            logger.exception(
                "Provider-specific normalization failed for %s; falling back to generic",
                provider,
            )

    user = user_payload or {}
    normalized = {
        "id": user.get("id") or user.get("sub") or user.get("user_id"),
        "email": user.get("email"),
        "full_name": None,
        "provider": None,
        "provider_id": None,
        "avatar_url": None,
    }

    meta = user.get("user_metadata") or user.get("app_metadata") or {}
    normalized["full_name"] = (
        meta.get("full_name")
        or meta.get("name")
        or user.get("name")
        or user.get("user_metadata", {}).get("name")
    )

    identities = user.get("identities") or []
    if identities and isinstance(identities, list) and identities:
        first = identities[0]
        normalized["provider"] = (first.get("provider") or "").lower()
        normalized["provider_id"] = first.get("id") or first.get("user_id") or first.get("sub")

    if not normalized["provider"]:
        p = detect_provider_from_payload({"user": user})
        normalized["provider"] = p

    if not normalized["provider_id"]:
        if user.get("sub"):
            normalized["provider_id"] = user.get("sub")
        elif meta.get("provider_id"):
            normalized["provider_id"] = meta.get("provider_id")

    normalized["avatar_url"] = (
        user.get("avatar_url") or meta.get("avatar_url") or user.get("picture")
    )
    return normalized
