"""High-level MCP Client wrapper.

Wraps the official MCP Python SDK session to provide higher-level methods for:
- Initializing connection & retrieving server info / capabilities
- Discovering tools, resources, and prompts
- Securely executing tool calls with timeout and response size enforcement
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.mcp.errors import MCPProtocolError, MCPTimeout, MCPToolCallFailed, MCPToolNotFound
from app.services.mcp.transport import connect_auto

logger = logging.getLogger("mcp.client")


class MCPClientManager:
    """Wrapper around MCP session operations."""

    def __init__(self, mcp_url: str, auth_headers: Optional[Dict[str, str]] = None, transport: str = "streamable-http"):
        self.mcp_url = mcp_url
        self.auth_headers = auth_headers or {}
        self.transport = transport

    async def discover_all(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Connect to MCP server and discover server info, tools, resources, and prompts.

        Returns:
            (server_info, tools, resources, prompts)
        """
        async with connect_auto(self.mcp_url, headers=self.auth_headers, preferred_transport=self.transport) as (session, transport_used):
            # 1. Server info & capabilities
            init_result = getattr(session, "init_result", None)
            server_info = {
                "transport": transport_used,
                "protocolVersion": getattr(init_result, "protocolVersion", "unknown") if init_result else "unknown",
                "server_name": getattr(getattr(init_result, "serverInfo", None), "name", "Unknown Server") if init_result else "Unknown Server",
                "server_version": getattr(getattr(init_result, "serverInfo", None), "version", "1.0.0") if init_result else "1.0.0",
                "capabilities": getattr(init_result, "capabilities", {}).model_dump() if hasattr(getattr(init_result, "capabilities", None), "model_dump") else {},
                "instructions": getattr(init_result, "instructions", None) if init_result else None,
            }

            # 2. Discover tools
            tools_list: List[Dict[str, Any]] = []
            try:
                result = await session.list_tools()
                for tool in result.tools:
                    tool_dict = {
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": tool.inputSchema if isinstance(tool.inputSchema, dict) else (tool.inputSchema.model_dump() if hasattr(tool.inputSchema, "model_dump") else {}),
                    }
                    tools_list.append(tool_dict)
            except Exception as exc:
                logger.warning("Failed to list tools for %s: %s", self.mcp_url, exc)

            # 3. Discover resources
            resources_list: List[Dict[str, Any]] = []
            try:
                res_result = await session.list_resources()
                for res in res_result.resources:
                    resources_list.append({
                        "uri": str(res.uri),
                        "name": res.name,
                        "description": res.description or "",
                        "mimeType": getattr(res, "mimeType", None),
                    })
            except Exception as exc:
                logger.debug("Resources discovery not supported or empty for %s: %s", self.mcp_url, exc)

            # 4. Discover prompts
            prompts_list: List[Dict[str, Any]] = []
            try:
                prompts_result = await session.list_prompts()
                for prompt in prompts_result.prompts:
                    prompts_list.append({
                        "name": prompt.name,
                        "description": prompt.description or "",
                        "arguments": [arg.model_dump() if hasattr(arg, "model_dump") else dict(arg) for arg in getattr(prompt, "arguments", []) or []],
                    })
            except Exception as exc:
                logger.debug("Prompts discovery not supported or empty for %s: %s", self.mcp_url, exc)

            return server_info, tools_list, resources_list, prompts_list

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call on the remote MCP server with safety limits."""
        timeout_seconds = float(getattr(settings, "MCP_TOOL_TIMEOUT_SECONDS", 60))
        max_bytes = int(getattr(settings, "MCP_MAX_RESPONSE_BYTES", 10_485_760))

        async with connect_auto(self.mcp_url, headers=self.auth_headers, preferred_transport=self.transport) as (session, _):
            try:
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                raise MCPTimeout(f"Tool '{tool_name}' call timed out after {timeout_seconds}s")
            except Exception as exc:
                logger.error("Error executing tool '%s' on %s: %s", tool_name, self.mcp_url, exc)
                raise MCPToolCallFailed(f"Remote MCP tool call failed: {exc}") from exc

            # Parse content
            content_items = []
            if hasattr(result, "content") and result.content:
                for item in result.content:
                    if hasattr(item, "text"):
                        content_items.append({"type": "text", "text": item.text})
                    elif hasattr(item, "blob"):
                        content_items.append({"type": "blob", "mimeType": getattr(item, "mimeType", ""), "data": item.blob})
                    elif hasattr(item, "model_dump"):
                        content_items.append(item.model_dump())
                    elif isinstance(item, dict):
                        content_items.append(item)
                    else:
                        content_items.append({"type": "text", "text": str(item)})

            response_payload = {
                "isError": getattr(result, "isError", False),
                "content": content_items,
            }

            # Enforce max response bytes check
            dumped = json.dumps(response_payload, ensure_ascii=False)
            if len(dumped.encode("utf-8")) > max_bytes:
                raise MCPToolCallFailed(f"Response size exceeded max limit of {max_bytes} bytes")

            return response_payload
