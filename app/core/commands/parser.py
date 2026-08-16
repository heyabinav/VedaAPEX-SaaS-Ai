from __future__ import annotations

import re
from typing import Any


def parse_command(message: str | None) -> dict[str, Any] | None:
    """Parse a slash command from a user message.

    Rules:
    - root slash only -> None (fallback to normal chat)
    - leading slash at start of message only
    - unknown commands return a structured fallback payload
    - double leading slash or mid-sentence slash are ignored
    """
    if message is None or not isinstance(message, str):
        return None

    stripped = message.strip()
    if not stripped:
        return None

    if stripped.startswith("//"):
        return None

    if not stripped.startswith("/"):
        return None

    if re.match(r"^/\S*$", stripped):
        if stripped == "/":
            return None
        command_name = stripped[1:]
        return {"command": command_name}

    match = re.match(r"^/([A-Za-z0-9_-]+)(?:\s+(.*))?$", stripped)
    if not match:
        return None

    command_name = match.group(1)
    remainder = (match.group(2) or "").strip()

    if not remainder:
        return {"command": command_name}

    args = remainder.split(maxsplit=1)
    subcommand = args[0]
    arguments = args[1] if len(args) > 1 else ""

    if command_name in {"skills", "agents", "mcp", "search", "images", "videos", "space", "research"}:
        payload: dict[str, Any] = {"command": command_name}

        if command_name in {"skills", "agents", "mcp"}:
            if subcommand:
                payload["subcommand"] = subcommand
            if arguments:
                payload["arguments"] = arguments
            return payload

        payload["arguments"] = remainder
        return payload

    return {
        "command": "unknown",
        "fallback_to_chat": True,
        "raw": stripped,
        "reason": f"Unknown command: {command_name}",
    }
