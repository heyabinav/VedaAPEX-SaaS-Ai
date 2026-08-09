"""SSRF protection and URL validation for MCP connector URLs.

Users can submit arbitrary URLs.  The backend MUST prevent requests to
internal services (localhost, private IPs, cloud metadata endpoints, etc.).
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

from app.core.config import settings
from app.services.mcp.errors import MCPInvalidURL, MCPSSRFBlocked

logger = logging.getLogger("mcp.security")

# ---------------------------------------------------------------------------
# Blocked hosts & IP ranges
# ---------------------------------------------------------------------------
_BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata.google.com",
})

_CLOUD_METADATA_IPS = frozenset({
    "169.254.169.254",  # AWS / GCP / Azure metadata
    "fd00:ec2::254",    # AWS IMDSv2 IPv6
})


def _is_private_or_blocked_ip(ip_str: str) -> bool:
    """Return True if the IP is private, loopback, link-local, or a known cloud metadata IP."""
    if ip_str in _CLOUD_METADATA_IPS:
        return True
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_mcp_url(url: str) -> str:
    """Validate and normalize an MCP server URL.

    Returns the cleaned URL on success.
    Raises MCPInvalidURL or MCPSSRFBlocked on failure.
    """
    if not url or not isinstance(url, str):
        raise MCPInvalidURL("MCP URL is required")

    url = url.strip()

    # 1) Parse & validate scheme
    try:
        parsed = urlparse(url)
    except Exception:
        raise MCPInvalidURL("Cannot parse MCP URL")

    if parsed.scheme not in ("http", "https"):
        raise MCPInvalidURL("MCP URL must use http or https")

    # 2) Must have a hostname
    hostname = (parsed.hostname or "").lower().strip(".")
    if not hostname:
        raise MCPInvalidURL("MCP URL must include a hostname")

    # 3) Block known bad hostnames
    if hostname in _BLOCKED_HOSTNAMES:
        raise MCPSSRFBlocked(f"Connections to '{hostname}' are blocked")

    # 4) Check if the hostname is itself an IP literal
    try:
        if _is_private_or_blocked_ip(hostname):
            raise MCPSSRFBlocked("Connections to private/internal IPs are blocked")
    except MCPSSRFBlocked:
        raise
    except Exception:
        pass  # Not an IP literal, proceed to DNS resolution

    # 5) HTTPS enforcement in production (after SSRF hostname/IP check)
    allow_http = getattr(settings, "MCP_ALLOW_HTTP_LOCAL_DEV", False)
    if parsed.scheme == "http" and not allow_http:
        raise MCPSSRFBlocked("HTTP scheme is blocked in production mode. Use HTTPS.")

    # 6) DNS resolution → validate all resolved IPs (rebinding protection)
    try:
        resolved = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise MCPInvalidURL(f"Cannot resolve hostname: {hostname}")

    for family, kind, proto, canonname, sockaddr in resolved:
        ip_str = sockaddr[0]
        if _is_private_or_blocked_ip(ip_str):
            raise MCPSSRFBlocked(
                "MCP URL resolves to a private/internal address"
            )

    # 7) Port validation — block common internal-only ports
    port = parsed.port
    if port and port in (25, 465, 587, 6379, 5432, 3306, 11211, 27017):
        raise MCPSSRFBlocked("MCP URL uses a blocked port")

    # 8) Build normalised URL
    path = parsed.path.rstrip("/") or ""
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"

    logger.info("MCP URL validated: %s", normalized)
    return normalized


def validate_redirect_url(url: str) -> str:
    """Validate that an OAuth redirect destination is safe."""
    if not url:
        raise MCPSSRFBlocked("Empty redirect URL")

    try:
        parsed = urlparse(url)
    except Exception:
        raise MCPSSRFBlocked("Cannot parse redirect URL")

    if parsed.scheme not in ("http", "https"):
        raise MCPSSRFBlocked("Redirect URL must use http or https")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise MCPSSRFBlocked("Redirect URL must include a hostname")

    if hostname in _BLOCKED_HOSTNAMES:
        raise MCPSSRFBlocked("Redirect to blocked hostname")

    try:
        if _is_private_or_blocked_ip(hostname):
            raise MCPSSRFBlocked("Redirect to private/internal IP is blocked")
    except MCPSSRFBlocked:
        raise
    except Exception:
        pass

    return url
