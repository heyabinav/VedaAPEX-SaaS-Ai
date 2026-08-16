"""MCP transport layer — uses the official MCP Python SDK.

Uses httpx client with SSE (Server-Sent Events) for reliable connections.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

from app.core.config import settings
from app.services.mcp.errors import MCPConnectionFailed, MCPTimeout

logger = logging.getLogger("mcp.transport")


def _get_connect_timeout() -> float:
    return float(getattr(settings, "MCP_CONNECTION_TIMEOUT_SECONDS", 30))


def _get_tool_timeout() -> float:
    return float(getattr(settings, "MCP_TOOL_TIMEOUT_SECONDS", 60))


@asynccontextmanager
async def connect_streamable_http(
    url: str,
    headers: dict[str, str] | None = None,
) -> AsyncGenerator[ClientSession, None]:
    """Connect to an MCP server using HTTP SSE transport.

    Yields a fully-initialized ClientSession ready for tool discovery / calls.
    """
    timeout = _get_connect_timeout()
    logger.info("Connecting via HTTP SSE: %s (timeout=%ss)", url, timeout)

    try:
        async with sse_client(
            url,
            headers=headers or {},
            timeout=timeout,
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                logger.info("MCP HTTP SSE session initialized: %s", url)
                yield session
    except asyncio.TimeoutError as exc:
        raise MCPTimeout(f"HTTP SSE connection timed out after {timeout}s") from exc
    except Exception as exc:
        logger.error("HTTP SSE connection failed for %s: %s", url, exc)
        raise MCPConnectionFailed(f"HTTP SSE connection failed: {type(exc).__name__}") from exc


@asynccontextmanager
async def connect_sse(
    url: str,
    headers: dict[str, str] | None = None,
) -> AsyncGenerator[ClientSession, None]:
    """Connect to an MCP server using SSE transport.

    Yields a fully-initialized ClientSession.
    """
    timeout = _get_connect_timeout()
    logger.info("Connecting via SSE: %s (timeout=%ss)", url, timeout)

    try:
        async with sse_client(
            url,
            headers=headers or {},
            timeout=timeout,
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                logger.info("MCP SSE session initialized: %s", url)
                yield session
    except asyncio.TimeoutError as exc:
        raise MCPTimeout(f"SSE connection timed out after {timeout}s") from exc
    except Exception as exc:
        logger.error("SSE connection failed for %s: %s", url, exc)
        raise MCPConnectionFailed(f"SSE connection failed: {type(exc).__name__}") from exc


@asynccontextmanager
async def connect_auto(
    url: str,
    headers: dict[str, str] | None = None,
    preferred_transport: str = "http-sse",
) -> AsyncGenerator[tuple[ClientSession, str], None]:
    """Connect to an MCP server using SSE transport.

    Yields (session, transport_used) where transport_used is "http-sse".
    """
    async with connect_streamable_http(url, headers) as session:
        yield session, "http-sse"
