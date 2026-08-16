from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AttachmentMetadata:
    id: str
    filename: str
    mime_type: str
    size: int
    extension: str
    temp_path: str
    is_image: bool = False
    is_document: bool = False
    sanitized_name: str = ""
    original_name: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedAttachment:
    attachment: AttachmentMetadata
    content: bytes
    text_preview: str | None = None
