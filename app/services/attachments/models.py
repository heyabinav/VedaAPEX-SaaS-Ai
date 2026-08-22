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
    asset_id: int | None = None
    proxy_url: str | None = None
    storage_key: str | None = None
    file_hash: str | None = None
    persisted: bool = False
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
