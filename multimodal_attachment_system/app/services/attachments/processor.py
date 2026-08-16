import io
import os
from pathlib import Path
from typing import Optional

from .config import ATTACHMENT_CONFIG
from .models import ParsedAttachment, AttachmentMetadata


class AttachmentProcessor:
    @staticmethod
    def is_valid_image_bytes(data: bytes) -> bool:
        return data[:3] in (b"\x89PNG", b"\xff\xd8\xff", b"RIF")

    @staticmethod
    def read_file_bytes(path: str) -> bytes:
        return Path(path).read_bytes()

    @staticmethod
    def safe_image_preview(metadata: AttachmentMetadata) -> bytes:
        return Path(metadata.temp_path).read_bytes()

    @staticmethod
    def extract_document_text(path: str, mime_type: str) -> Optional[str]:
        data = Path(path).read_bytes()
        if mime_type == "application/pdf":
            return "[PDF attachment detected; document text extraction should be implemented by provider-specific strategy.]"
        if mime_type in {"text/plain", "text/csv"}:
            text = data.decode("utf-8", errors="replace")
            return text[: ATTACHMENT_CONFIG.MAX_DOCUMENT_CHARACTERS]
        return None

    @staticmethod
    def parse_attachment(metadata: AttachmentMetadata) -> ParsedAttachment:
        data = Path(metadata.temp_path).read_bytes()
        text_preview = None
        if metadata.is_document:
            text_preview = AttachmentProcessor.extract_document_text(metadata.temp_path, metadata.mime_type)
        return ParsedAttachment(
            attachment=metadata,
            content=data,
            text_preview=text_preview,
        )
