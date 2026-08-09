"""MCP authentication requirement discovery and probing.

Probes remote MCP server endpoints to determine:
- If authentication is required (401 response)
- If OAuth is required (WWW-Authenticate header with OAuth info)
- If public / no authentication is required (200 response or successful MCP handshake)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from app.services.mcp.oauth import MCPOAuthService
from app.services.mcp.security import validate_mcp_url
from app.services.mcp.transport import connect_streamable_http

logger = logging.getLogger("mcp.discovery")


@dataclass
class AuthRequirement:
    auth_required: bool
    auth_type: str  # "none" or "oauth"
    www_authenticate: Optional[str] = None
    oauth_config: Optional[Dict[str, Any]] = None


class MCPDiscoveryService:
    """Probes remote MCP server URLs to detect auth requirements."""

    @staticmethod
    async def probe_authentication(mcp_url: str) -> AuthRequirement:
        """Probe the MCP URL to discover auth requirements."""
        clean_url = validate_mcp_url(mcp_url)

        # 1. First attempt a probe GET or POST to check HTTP status
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            try:
                resp = await client.get(clean_url)
                if resp.status_code == 401:
                    www_auth = resp.headers.get("www-authenticate")
                    logger.info("Probe GET returned 401. WWW-Authenticate: %s", www_auth)
                    oauth_cfg = await MCPOAuthService.discover_oauth_config(clean_url, www_auth)
                    return AuthRequirement(
                        auth_required=True,
                        auth_type="oauth",
                        www_authenticate=www_auth,
                        oauth_config=oauth_cfg,
                    )
            except Exception as exc:
                logger.debug("Probe GET failed for %s: %s", clean_url, exc)

        # 2. Try Streamable HTTP connection attempt
        try:
            async with connect_streamable_http(clean_url) as session:
                logger.info("Direct MCP connect successful for %s. No auth required.", clean_url)
                return AuthRequirement(
                    auth_required=False,
                    auth_type="none",
                )
        except Exception as exc:
            err_msg = str(exc).lower()
            if "401" in err_msg or "unauthorized" in err_msg or "auth" in err_msg:
                logger.info("Direct connect failed with 401/unauthorized for %s", clean_url)
                oauth_cfg = await MCPOAuthService.discover_oauth_config(clean_url)
                return AuthRequirement(
                    auth_required=True,
                    auth_type="oauth",
                    oauth_config=oauth_cfg,
                )
            logger.warning("MCP probe encountered error for %s: %s. Assuming direct connection or retry.", clean_url, exc)

        # Default fallback: attempt direct connection
        return AuthRequirement(
            auth_required=False,
            auth_type="none",
        )
