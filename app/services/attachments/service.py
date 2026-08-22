from __future__ import annotations

import logging
from typing import Any

from fastapi import UploadFile
from sqlmodel import Session

from app.services.attachments.config import ATTACHMENT_CONFIG
from app.services.attachments.models import AttachmentMetadata
from app.services.attachments.storage import TemporaryAttachmentStorage
from app.services.attachments.validator import (
    AttachmentValidationError,
    validate_file_metadata,
    validate_image_content,
)
from app.services.asset_storage_service import asset_storage


logger = logging.getLogger("services.attachments.service")


class AttachmentService:
    @staticmethod
    async def process(
        files: list[UploadFile] | None,
        user_id: Any,
        session: Session | None = None,
        persist: bool = True,
    ) -> tuple[list[AttachmentMetadata], list[dict[str, Any]]]:
        if not files:
            return [], []

        if len(files) > ATTACHMENT_CONFIG.MAX_FILES_PER_REQUEST:
            raise AttachmentValidationError("TOO_MANY_FILES", "Too many files uploaded for a single request.")

        attachments: list[AttachmentMetadata] = []
        normalized: list[dict[str, Any]] = []

        for file in files:
            filename = getattr(file, "filename", "") or "upload.bin"
            mime_type = getattr(file, "content_type", "") or "application/octet-stream"
            file_bytes = await file.read()
            size = len(file_bytes)
            validate_file_metadata(filename, mime_type, size)
            validate_image_content(file_bytes, mime_type)

            if len(file_bytes) > ATTACHMENT_CONFIG.MAX_FILE_SIZE:
                raise AttachmentValidationError("FILE_TOO_LARGE", "The uploaded file exceeds the maximum allowed size.")

            attachment = TemporaryAttachmentStorage.save_upload(file_bytes, filename, mime_type)
            attachments.append(attachment)
            normalized_item = {
                "id": attachment.id,
                "filename": attachment.filename,
                "mime_type": attachment.mime_type,
                "size": attachment.size,
                "temp_path": attachment.temp_path,
                "path": attachment.temp_path,
                "data": file_bytes,
                "persistent": False,
            }

            if persist and session is not None:
                try:
                    stored_asset = asset_storage.upload_asset(
                        session,
                        user_id=int(user_id),
                        local_path=attachment.temp_path,
                        original_filename=attachment.filename,
                        provider="chat-upload",
                    )
                    attachment.asset_id = stored_asset.id
                    attachment.proxy_url = stored_asset.proxy_url
                    attachment.storage_key = stored_asset.r2_object_key
                    attachment.file_hash = stored_asset.file_hash
                    attachment.persisted = True
                    normalized_item.update(
                        {
                            "asset_id": stored_asset.id,
                            "proxy_url": stored_asset.proxy_url,
                            "storage_key": stored_asset.r2_object_key,
                            "file_hash": stored_asset.file_hash,
                            "persistent": True,
                        }
                    )
                except Exception as exc:
                    logger.warning(
                        "Attachment persistence failed for user_id=%s filename=%s: %s",
                        user_id,
                        filename,
                        exc,
                    )

            normalized.append(normalized_item)

        return attachments, normalized

    @staticmethod
    def cleanup(attachments: list[AttachmentMetadata]) -> None:
        TemporaryAttachmentStorage.cleanup_many(attachments)
