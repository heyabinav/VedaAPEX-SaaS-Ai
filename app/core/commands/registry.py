from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandDefinition:
    name: str
    description: str
    category: str
    handler: str | None = None
    permission: str = "user"
    required_plan: str | None = None
    required_tools: list[str] = field(default_factory=list)
    enabled: bool = False
    aliases: list[str] = field(default_factory=list)


class CommandRegistry:
    """Simple in-memory registry for phased command plumbing."""

    def __init__(self):
        self._commands: dict[str, CommandDefinition] = {}

    def register(self, command: CommandDefinition) -> None:
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command

    def get(self, name: str) -> CommandDefinition | None:
        return self._commands.get(name)

    def list(self) -> list[CommandDefinition]:
        ordered = []
        seen: set[str] = set()
        for command in self._commands.values():
            key = command.name
            if key in seen:
                continue
            seen.add(key)
            ordered.append(command)
        return ordered

    def enabled(self) -> list[CommandDefinition]:
        return [cmd for cmd in self.list() if cmd.enabled]


registry = CommandRegistry()


def _register_placeholder_commands() -> None:
    placeholders = [
        CommandDefinition(
            name="skills",
            description="List or run registered skills.",
            category="skills",
            handler="skills_handler",
            permission="user",
            required_plan=None,
            required_tools=[],
            enabled=False,
            aliases=["skill"],
        ),
        CommandDefinition(
            name="agents",
            description="List or run agent workflows.",
            category="agents",
            handler="agents_handler",
            permission="user",
            required_plan=None,
            required_tools=[],
            enabled=False,
            aliases=["agent"],
        ),
        CommandDefinition(
            name="tools",
            description="List available tools.",
            category="tools",
            handler="tools_handler",
            permission="user",
            required_plan=None,
            required_tools=[],
            enabled=False,
            aliases=["tool"],
        ),
        CommandDefinition(
            name="search",
            description="Unified search router.",
            category="search",
            handler="search_handler",
            permission="user",
            required_plan=None,
            required_tools=[],
            enabled=False,
            aliases=["find"],
        ),
        CommandDefinition(
            name="images",
            description="Image search command.",
            category="search",
            handler="images_handler",
            permission="user",
            required_plan=None,
            required_tools=["image_search"],
            enabled=False,
            aliases=["image", "img"],
        ),
        CommandDefinition(
            name="videos",
            description="Video search command.",
            category="search",
            handler="videos_handler",
            permission="user",
            required_plan=None,
            required_tools=["video_search"],
            enabled=False,
            aliases=["video"],
        ),
        CommandDefinition(
            name="space",
            description="Space and NASA research search.",
            category="search",
            handler="space_handler",
            permission="user",
            required_plan=None,
            required_tools=["space_search"],
            enabled=False,
            aliases=["nasa"],
        ),
        CommandDefinition(
            name="research",
            description="Research workflow placeholder.",
            category="agents",
            handler="research_handler",
            permission="user",
            required_plan=None,
            required_tools=["web_search"],
            enabled=False,
            aliases=["r"],
        ),
        CommandDefinition(
            name="help",
            description="Display available command list.",
            category="system",
            handler="help_handler",
            permission="user",
            required_plan=None,
            required_tools=[],
            enabled=True,
            aliases=["?"],
        ),
        CommandDefinition(
            name="status",
            description="Check execution status by request_id.",
            category="system",
            handler="status_handler",
            permission="user",
            required_plan=None,
            required_tools=[],
            enabled=True,
            aliases=["state"],
        ),
    ]

    for command in placeholders:
        registry.register(command)


_register_placeholder_commands()


def list_command_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": command.name,
            "description": command.description,
            "category": command.category,
            "handler": command.handler,
            "permission": command.permission,
            "required_plan": command.required_plan,
            "required_tools": command.required_tools,
            "enabled": command.enabled,
            "aliases": command.aliases,
        }
        for command in registry.enabled()
    ]
