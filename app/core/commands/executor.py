from __future__ import annotations

from typing import Any

from app.core.commands.parser import parse_command
from app.core.commands.registry import registry, list_command_definitions


class CommandExecutionError(ValueError):
    """Raised when a command payload is malformed or unsupported."""


def validate_command_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize command payloads into a consistent execution contract."""
    if payload is None:
        raise CommandExecutionError("Command payload is required.")

    if not isinstance(payload, dict):
        raise CommandExecutionError("Command payload must be an object.")

    if "message" in payload and isinstance(payload["message"], str):
        parsed = parse_command(payload["message"])
        if parsed is not None:
            return parsed

    if "command" in payload:
        command_name = str(payload["command"]).strip().lower()
        if not command_name:
            raise CommandExecutionError("Command name is required.")
        result = {"command": command_name}
        for key in ("subcommand", "arguments", "raw"):
            if key in payload and payload[key] not in (None, ""):
                result[key] = payload[key]
        return result

    raise CommandExecutionError("Command payload must include a message or command field.")


def _snapshot_registry() -> dict[str, Any]:
    return {
        "count": len(list_command_definitions()),
        "commands": list_command_definitions(),
    }


def execute_command(command_input: str | dict[str, Any] | None, *, user_id: int | None = None) -> dict[str, Any]:
    """Execute a parsed or raw command payload.

    This is a phased execution layer: command handlers are intentionally stubbed and
    return structured metadata instead of invoking live provider/tool flows.
    """
    if command_input is None:
        raise CommandExecutionError("Command input is required.")

    payload = parse_command(command_input) if isinstance(command_input, str) else validate_command_payload(command_input)
    if payload is None:
        raise CommandExecutionError("No valid command was detected in the provided input.")

    command_name = str(payload.get("command", "")).strip().lower()
    if not command_name:
        raise CommandExecutionError("Command name is missing.")

    command_def = registry.get(command_name)
    if command_def is None:
        return {
            "success": False,
            "command": command_name,
            "status": "rejected",
            "message": "Command is not registered.",
            "fallback_to_chat": True,
            "raw": payload,
            "user_id": user_id,
        }

    if not command_def.enabled:
        return {
            "success": False,
            "command": command_name,
            "status": "disabled",
            "message": "Command is registered but disabled in the current phase.",
            "fallback_to_chat": True,
            "registry": _snapshot_registry(),
            "user_id": user_id,
        }

    response: dict[str, Any] = {
        "success": True,
        "command": command_name,
        "status": "accepted",
        "message": f"{command_name} command accepted for execution.",
        "execution": {
            "phase": "plumbing",
            "handler": command_def.handler,
            "category": command_def.category,
            "permission": command_def.permission,
            "required_tools": command_def.required_tools,
            "required_plan": command_def.required_plan,
            "user_id": user_id,
            "supported": True,
        },
        "parsed": payload,
        "registry": _snapshot_registry(),
    }

    if "subcommand" in payload:
        response["subcommand"] = payload["subcommand"]
    if "arguments" in payload:
        response["arguments"] = payload["arguments"]
    if "raw" in payload:
        response["raw"] = payload["raw"]

    return response
