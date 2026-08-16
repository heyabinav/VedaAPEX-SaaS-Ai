from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    @abstractmethod
    async def supports_vision(self, model: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def prepare_messages(self, message: str, attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def generate(self, messages: list[dict[str, Any]], model: str, provider: str) -> Any:
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    async def supports_vision(self, model: str) -> bool:
        return model.lower().startswith(("gpt-4o", "gpt-4.1", "gpt-4-turbo"))

    async def prepare_messages(self, message: str, attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = [{"type": "text", "text": message}]
        for attachment in attachments:
            if attachment.get("mime_type", "").startswith("image/"):
                content.append({"type": "image", "data": attachment.get("data", "")})
        return [{"role": "user", "content": content}]

    async def generate(self, messages: list[dict[str, Any]], model: str, provider: str) -> Any:
        return {"messages": messages, "model": model, "provider": provider}


class GeminiProvider(AIProvider):
    async def supports_vision(self, model: str) -> bool:
        return "gemini" in model.lower() or "vision" in model.lower()

    async def prepare_messages(self, message: str, attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        parts = [{"text": message}]
        for attachment in attachments:
            if attachment.get("mime_type", "").startswith("image/"):
                parts.append({"inline_data": {"mime_type": attachment.get("mime_type"), "data": attachment.get("data", "")}})
        return [{"role": "user", "parts": parts}]

    async def generate(self, messages: list[dict[str, Any]], model: str, provider: str) -> Any:
        return {"messages": messages, "model": model, "provider": provider}


class QwenProvider(AIProvider):
    async def supports_vision(self, model: str) -> bool:
        return "qwen" in model.lower() and "vl" in model.lower()

    async def prepare_messages(self, message: str, attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        content = [{"type": "text", "text": message}]
        for attachment in attachments:
            if attachment.get("mime_type", "").startswith("image/"):
                content.append({"type": "image", "data": attachment.get("data", "")})
        return [{"role": "user", "content": content}]

    async def generate(self, messages: list[dict[str, Any]], model: str, provider: str) -> Any:
        return {"messages": messages, "model": model, "provider": provider}


class AnthropicProvider(AIProvider):
    async def supports_vision(self, model: str) -> bool:
        return "claude" in model.lower() and "vision" in model.lower()

    async def prepare_messages(self, message: str, attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        content = [{"type": "text", "text": message}]
        for attachment in attachments:
            if attachment.get("mime_type", "").startswith("image/"):
                content.append({"type": "image", "source": attachment.get("data", "")})
        return [{"role": "user", "content": content}]

    async def generate(self, messages: list[dict[str, Any]], model: str, provider: str) -> Any:
        return {"messages": messages, "model": model, "provider": provider}
