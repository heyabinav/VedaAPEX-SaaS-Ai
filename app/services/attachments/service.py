from __future__ import annotations

from typing import Any

from fastapi import UploadFile

from app.services.attachments.config import ATTACHMENT_CONFIG
from app.services.attachments.models import AttachmentMetadata
from app.services.attachments.storage import TemporaryAttachmentStorage
from app.services.attachments.validator import AttachmentValidationError, validate_file_metadata


class AttachmentService:
    @staticmethod
    async def process(files: list[UploadFile] | None, user_id: Any) -> tuple[list[AttachmentMetadata], list[dict[str, Any]]]:
        if not files:
            return [], []

        if len(files) > ATTACHMENT_CONFIG.MAX_FILES_PER_REQUEST:
            raise AttachmentValidationError("TOO_MANY_FILES", "Too many files uploaded for a single request.")

        attachments: list[AttachmentMetadata] = []
        normalized: list[dict[str, Any]] = []

        for file in files:
            filename = getattr(file, "filename", "") or "upload.bin"
            mime_type = getattr(file, "content_type", "") or "application/octet-stream"
            size = getattr(file, "size", 0) or 0
            validate_file_metadata(filename, mime_type, size)
            file_bytes = await file.read()

            if len(file_bytes) > ATTACHMENT_CONFIG.MAX_FILE_SIZE:
                raise AttachmentValidationError("FILE_TOO_LARGE", "The uploaded file exceeds the maximum allowed size.")

            attachment = TemporaryAttachmentStorage.save_upload(file_bytes, filename, mime_type)
            attachments.append(attachment)
            normalized.append({
                "id": attachment.id,
                "filename": attachment.filename,
                "mime_type": attachment.mime_type,
                "size": attachment.size,
                "temp_path": attachment.temp_path,
                "path": attachment.temp_path,
                "data": file_bytes,
            })

        return attachments, normalized

    @staticmethod
    def cleanup(attachments: list[AttachmentMetadata]) -> None:
        TemporaryAttachmentStorage.cleanup_many(attachments)
