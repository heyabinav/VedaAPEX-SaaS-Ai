from __future__ import annotations

from typing import Any

from app.core.commands.parser import parse_command


class CommandValidationError(ValueError):
    """Raised when a command is malformed or invalid."""


def validate_command_text(message: str | None) -> dict[str, Any]:
    """Return a normalized validation object for a slash-command text input."""
    if message is None or not isinstance(message, str):
        raise CommandValidationError("Message must be a non-empty string.")

    stripped = message.strip()
    if not stripped:
        raise CommandValidationError("Message cannot be empty.")

    parsed = parse_command(stripped)
    if parsed is None:
        raise CommandValidationError("Input is not a valid slash command.")

    return parsed


def validate_command_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Validate a structured command payload and normalize it."""
    if payload is None or not isinstance(payload, dict):
        raise CommandValidationError("Command payload must be a dictionary.")

    command_name = payload.get("command")
    if command_name is None:
        raise CommandValidationError("Payload must include a command name.")

    normalized = {"command": str(command_name).strip().lower()}
    for key in ("subcommand", "arguments", "raw"):
        if key in payload and payload[key] not in (None, ""):
            normalized[key] = payload[key]
    return normalized
