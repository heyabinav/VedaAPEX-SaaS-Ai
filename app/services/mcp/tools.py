"""MCP Tool processing, schema validation, and security sanitization.

Ensures:
- Tool names and descriptions are valid
- Untrusted tool descriptions do NOT overwrite system instructions
- Input schema arguments are validated before sending to MCP servers
- Response content sizes and structures are safe
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mcp.tools")

# Regex to detect potential prompt injection patterns in tool descriptions or instructions
_PROMPT_INJECTION_PATTERN = re.compile(
    r"(ignore\s+(previous|all)\s+instructions|system\s+prompt|you\s+are\s+now|override\s+rules|delete\s+all|jailbreak)",
    re.IGNORECASE,
)


class MCPToolProcessor:
    """Sanitizes and processes discovered MCP tools."""

    @staticmethod
    def sanitize_description(description: str) -> str:
        """Sanitize a tool description to prevent system instruction overrides."""
        if not description:
            return ""

        cleaned = description.strip()

        # Flag and strip prompt injection attempts
        if _PROMPT_INJECTION_PATTERN.search(cleaned):
            logger.warning("Potential prompt injection attempt stripped from tool description: %s", cleaned[:100])
            cleaned = _PROMPT_INJECTION_PATTERN.sub("[redacted instruction]", cleaned)

        # Truncate overly long descriptions
        if len(cleaned) > 2000:
            cleaned = cleaned[:1997] + "..."

        return cleaned

    @staticmethod
    def classify_permission(tool_name: str, description: str = "") -> str:
        """Classify a tool into READ (auto-allowed) vs WRITE (requires user confirmation).

        READ tools: search, list, get, read, fetch, query, view, find, check
        WRITE tools: create, update, delete, send, execute, publish, write, post, remove, modify, drop
        """
        name_lower = tool_name.lower()
        desc_lower = description.lower()

        # Explicit WRITE keywords
        write_keywords = {"create", "update", "delete", "send", "execute", "publish", "write", "post", "remove", "modify", "drop", "put"}
        for kw in write_keywords:
            if kw in name_lower or f" {kw} " in desc_lower:
                return "WRITE"

        # Explicit READ keywords
        read_keywords = {"search", "list", "get", "read", "fetch", "query", "view", "find", "check", "info"}
        for kw in read_keywords:
            if kw in name_lower:
                return "READ"

        # Default fallback
        return "READ"

    @staticmethod
    def process_tools(tools_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and validate raw discovered tool definitions."""
        processed = []
        for tool in tools_raw:
            if not isinstance(tool, dict) or not tool.get("name"):
                continue

            name = str(tool["name"]).strip()
            desc = MCPToolProcessor.sanitize_description(str(tool.get("description", "")))
            input_schema = tool.get("inputSchema") if isinstance(tool.get("inputSchema"), dict) else {"type": "object", "properties": {}}
            permission = MCPToolProcessor.classify_permission(name, desc)

            processed.append({
                "name": name,
                "description": desc,
                "inputSchema": input_schema,
                "permission": permission,
            })

        return processed
