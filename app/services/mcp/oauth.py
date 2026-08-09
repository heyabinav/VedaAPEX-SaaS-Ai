"""MCP OAuth 2.0 service.

Handles:
- Protected resource metadata discovery (RFC 9728)
- Authorization server metadata discovery (RFC 8414)
- PKCE generation (code_verifier & code_challenge S256)
- State generation & SHA-256 hashed storage
- Dynamic Client Registration (RFC 7591) / Client ID Metadata Documents
- Authorization URL construction
- Code exchange & token refresh
- Secure token storage using authenticated Fernet encryption (secret_vault)
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from app.core.config import settings
from app.services.mcp.errors import (
    MCPOAuthDenied,
    MCPOAuthDiscoveryFailed,
    MCPOAuthStateInvalid,
    MCPTokenExchangeFailed,
    MCPTokenRefreshFailed,
)
from app.services.mcp.security import validate_redirect_url
from app.services.secret_vault import decrypt_text, encrypt_text
from app.utils.time import utcnow

logger = logging.getLogger("mcp.oauth")


def generate_pkce() -> Tuple[str, str]:
    """Generate PKCE code_verifier and S256 code_challenge."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def generate_state() -> str:
    """Generate a secure random OAuth state string."""
    return secrets.token_urlsafe(32)


def hash_state(state: str) -> str:
    """Hash state for safe DB lookup without storing raw state string."""
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


class MCPOAuthService:
    """Handles OAuth 2.0 discovery, client registration, and token lifecycle for MCP servers."""

    @staticmethod
    async def discover_oauth_config(mcp_url: str, www_auth_header: Optional[str] = None) -> Dict[str, Any]:
        """Discover Authorization Server metadata for an MCP server.

        Supports:
        1. WWW-Authenticate header resource metadata URL (RFC 9728)
        2. Well-known authorization server metadata (RFC 8414 / OpenID Connect)
        """
        parsed_mcp = urlparse(mcp_url)
        base_url = f"{parsed_mcp.scheme}://{parsed_mcp.netloc}"

        auth_server_url: Optional[str] = None

        # 1. Try parsing WWW-Authenticate header if present
        if www_auth_header:
            logger.info("Parsing WWW-Authenticate header: %s", www_auth_header)
            # Look for resource_metadata="https://..." or authorization_uri="https://..."
            for param in www_auth_header.split(","):
                param = param.strip()
                if "=" in param:
                    key, val = param.split("=", 1)
                    val = val.strip('"\'')
                    if key.lower() in ("resource_metadata", "authorization_server", "as_uri"):
                        auth_server_url = val
                        break

        # 2. Probe well-known endpoints if not resolved from header
        candidates = []
        if auth_server_url:
            candidates.append(auth_server_url)

        candidates.extend([
            f"{base_url}/.well-known/oauth-authorization-server",
            f"{base_url}/.well-known/openid-configuration",
            f"{base_url}/oauth/.well-known/openid-configuration",
        ])

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for endpoint in candidates:
                try:
                    resp = await client.get(endpoint)
                    if resp.status_code == 200:
                        data = resp.json()
                        if "authorization_endpoint" in data and "token_endpoint" in data:
                            logger.info("Discovered OAuth metadata from %s", endpoint)
                            return {
                                "issuer": data.get("issuer", base_url),
                                "authorization_endpoint": data["authorization_endpoint"],
                                "token_endpoint": data["token_endpoint"],
                                "registration_endpoint": data.get("registration_endpoint"),
                                "scopes_supported": data.get("scopes_supported", ["mcp", "openid", "profile"]),
                                "code_challenge_methods_supported": data.get("code_challenge_methods_supported", ["S256"]),
                                "metadata_source": endpoint,
                            }
                except Exception as exc:
                    logger.debug("OAuth discovery failed for endpoint %s: %s", endpoint, exc)

        # Direct fallback heuristic if well-known fails
        fallback_auth = f"{base_url}/oauth/authorize"
        fallback_token = f"{base_url}/oauth/token"
        logger.warning("OAuth well-known discovery failed for %s. Using heuristic fallbacks: %s, %s", mcp_url, fallback_auth, fallback_token)
        return {
            "issuer": base_url,
            "authorization_endpoint": fallback_auth,
            "token_endpoint": fallback_token,
            "registration_endpoint": f"{base_url}/oauth/register",
            "scopes_supported": ["mcp"],
            "code_challenge_methods_supported": ["S256"],
            "metadata_source": "fallback",
        }

    @staticmethod
    async def register_dynamic_client(registration_endpoint: str, redirect_uri: str, client_name: str = "VedaApex MCP Connector") -> Optional[str]:
        """Perform Dynamic Client Registration (RFC 7591) if supported by the authorization server."""
        if not registration_endpoint:
            return None

        payload = {
            "client_name": client_name,
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",  # Public client with PKCE
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(registration_endpoint, json=payload)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    client_id = data.get("client_id")
                    logger.info("Dynamic Client Registration succeeded: client_id=%s", client_id)
                    return client_id
        except Exception as exc:
            logger.warning("Dynamic Client Registration failed at %s: %s", registration_endpoint, exc)

        return None

    @staticmethod
    def build_authorization_url(
        authorization_endpoint: str,
        client_id: str,
        redirect_uri: str,
        state: str,
        code_challenge: str,
        scope: str = "mcp",
    ) -> str:
        """Construct the full OAuth 2.0 authorization URL with PKCE."""
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "scope": scope,
        }
        delimiter = "&" if "?" in authorization_endpoint else "?"
        return f"{authorization_endpoint}{delimiter}{urlencode(params)}"

    @staticmethod
    async def exchange_code_for_tokens(
        token_endpoint: str,
        code: str,
        redirect_uri: str,
        client_id: str,
        code_verifier: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": code_verifier,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        logger.info("Exchanging OAuth authorization code at endpoint %s", token_endpoint)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(token_endpoint, data=data, headers=headers)
            if resp.status_code != 200:
                logger.error("Token exchange failed HTTP %d: %s", resp.status_code, resp.text)
                raise MCPTokenExchangeFailed(f"Token exchange failed with HTTP {resp.status_code}")

            try:
                payload = resp.json()
            except Exception as exc:
                raise MCPTokenExchangeFailed("Token endpoint returned non-JSON response") from exc

            access_token = payload.get("access_token")
            if not access_token:
                raise MCPTokenExchangeFailed("Token response missing access_token")

            expires_in = payload.get("expires_in")
            expires_at = utcnow() + timedelta(seconds=int(expires_in)) if expires_in else None

            return {
                "access_token": access_token,
                "refresh_token": payload.get("refresh_token"),
                "token_type": payload.get("token_type", "Bearer"),
                "expires_at": expires_at,
                "scope": payload.get("scope"),
            }

    @staticmethod
    async def refresh_tokens(
        token_endpoint: str,
        refresh_token: str,
        client_id: str,
    ) -> Dict[str, Any]:
        """Refresh expired access token using refresh_token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        logger.info("Refreshing access token at endpoint %s", token_endpoint)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(token_endpoint, data=data, headers=headers)
            if resp.status_code != 200:
                logger.error("Token refresh failed HTTP %d: %s", resp.status_code, resp.text)
                raise MCPTokenRefreshFailed(f"Token refresh failed with HTTP {resp.status_code}")

            try:
                payload = resp.json()
            except Exception as exc:
                raise MCPTokenRefreshFailed("Token endpoint returned invalid JSON") from exc

            access_token = payload.get("access_token")
            if not access_token:
                raise MCPTokenRefreshFailed("Token refresh response missing access_token")

            expires_in = payload.get("expires_in")
            expires_at = utcnow() + timedelta(seconds=int(expires_in)) if expires_in else None

            return {
                "access_token": access_token,
                "refresh_token": payload.get("refresh_token") or refresh_token,  # Keep old if not rotated
                "token_type": payload.get("token_type", "Bearer"),
                "expires_at": expires_at,
                "scope": payload.get("scope"),
            }
