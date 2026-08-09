"""MCP Tool Registry and Namespacing service.

Ensures every discovered MCP tool is internally namespaced to prevent collisions.
Format: mcp_{connector_id}_{tool_name}

Example:
Connector ID: 12
Original tool: search
Internal tool name: mcp_12_search
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mcp.registry")


class MCPToolRegistry:
    """Registry and namespacing manager for user MCP tools."""

    @staticmethod
    def namespace_tool_name(connector_id: int, original_name: str) -> str:
        """Generate namespaced tool identifier."""
        clean_name = original_name.strip().replace("-", "_")
        return f"mcp_{connector_id}_{clean_name}"

    @staticmethod
    def parse_namespaced_name(namespaced_name: str) -> Optional[tuple[int, str]]:
        """Parse namespaced tool identifier into (connector_id, original_tool_name)."""
        parts = namespaced_name.split("_", 2)
        if len(parts) == 3 and parts[0] == "mcp" and parts[1].isdigit():
            return int(parts[1]), parts[2]
        return None

    @staticmethod
    def build_ai_tool_definitions(connector_id: int, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build AI tool definitions for LLM tool-calling registries."""
        ai_tools = []
        for tool in tools:
            original_name = tool.get("name", "")
            if not original_name:
                continue

            namespaced = MCPToolRegistry.namespace_tool_name(connector_id, original_name)
            ai_tools.append({
                "type": "function",
                "function": {
                    "name": namespaced,
                    "description": f"[MCP Connector #{connector_id}] {tool.get('description', '')}",
                    "parameters": tool.get("inputSchema") or {"type": "object", "properties": {}},
                },
                "original_name": original_name,
                "connector_id": connector_id,
                "permission": tool.get("permission", "READ"),
            })
        return ai_tools
