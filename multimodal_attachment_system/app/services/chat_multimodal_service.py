from __future__ import annotations

import os
from typing import Any

from .attachments.config import ATTACHMENT_CONFIG
from .attachments.models import AttachmentMetadata
from .attachments.processor import AttachmentProcessor
from .attachments.storage import TemporaryAttachmentStorage
from .attachments.validator import AttachmentValidationError, validate_file_metadata


class MultimodalChatService:
    @staticmethod
    async def process_and_validate_uploads(files: list[Any], message: str) -> tuple[list[AttachmentMetadata], list[dict[str, Any]]]:
        if not files:
            return [], []

        if len(files) > ATTACHMENT_CONFIG.MAX_FILES_PER_REQUEST:
            raise AttachmentValidationError("TOO_MANY_FILES", "Too many files uploaded for a single request.")

        attachments: list[AttachmentMetadata] = []
        prepared: list[dict[str, Any]] = []

        for upload in files:
            filename = getattr(upload, "filename", "") or "upload.bin"
            mime_type = getattr(upload, "content_type", "") or "application/octet-stream"
            size = getattr(upload, "size", 0) or 0
            validate_file_metadata(filename=filename, mime_type=mime_type, size=size)

            file_bytes = await upload.read()
            metadata = TemporaryAttachmentStorage.save_upload(file_bytes, filename, mime_type)
            attachments.append(metadata)
            prepared.append({
                "id": metadata.id,
                "filename": metadata.filename,
                "mime_type": metadata.mime_type,
                "size": metadata.size,
                "temp_path": metadata.temp_path,
                "data": file_bytes,
            })

        return attachments, prepared

    @staticmethod
    async def build_multimodal_messages(message: str, attachments: list[dict[str, Any]], model: str = "gpt-4o") -> list[dict[str, Any]]:
        normalized = [{"role": "user", "content": [{"type": "text", "text": message}]}]
        for item in attachments:
            mime_type = item.get("mime_type", "")
            if mime_type.startswith("image/"):
                normalized[0]["content"].append({
                    "type": "image",
                    "data": item.get("data", ""),
                })
        return normalized

    @staticmethod
    async def cleanup_after_request(attachments: list[AttachmentMetadata]) -> None:
        TemporaryAttachmentStorage.cleanup_many(attachments)
