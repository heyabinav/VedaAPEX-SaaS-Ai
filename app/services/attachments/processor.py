from pathlib import Path
from typing import Optional

from .config import ATTACHMENT_CONFIG
from .models import AttachmentMetadata, ParsedAttachment


class AttachmentProcessor:
    @staticmethod
    def read_file_bytes(path: str) -> bytes:
        return Path(path).read_bytes()

    @staticmethod
    def extract_document_text(path: str, mime_type: str) -> Optional[str]:
        raw = Path(path).read_bytes()
        if mime_type == "application/pdf":
            return "[PDF attachment provided; provider-specific PDF parsing should be used when supported.]"
        if mime_type in {"text/plain", "text/csv"}:
            text = raw.decode("utf-8", errors="replace")
            return text[: ATTACHMENT_CONFIG.MAX_DOCUMENT_CHARACTERS]
        return None

    @staticmethod
    def parse_attachment(metadata: AttachmentMetadata) -> ParsedAttachment:
        content = Path(metadata.temp_path).read_bytes()
        text_preview = None
        if metadata.is_document:
            text_preview = AttachmentProcessor.extract_document_text(metadata.temp_path, metadata.mime_type)
        return ParsedAttachment(
            attachment=metadata,
            content=content,
            text_preview=text_preview,
        )
