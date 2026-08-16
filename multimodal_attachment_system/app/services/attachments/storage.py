import os
import shutil
import tempfile
import uuid
from pathlib import Path

from .config import ATTACHMENT_CONFIG
from .models import AttachmentMetadata
from .validator import sanitize_filename


class TemporaryAttachmentStorage:
    @staticmethod
    def ensure_root() -> str:
        root = Path(ATTACHMENT_CONFIG.TEMP_UPLOAD_DIR)
        root.mkdir(parents=True, exist_ok=True)
        return str(root)

    @staticmethod
    def save_upload(file_bytes: bytes, original_filename: str, mime_type: str) -> AttachmentMetadata:
        safe_name = sanitize_filename(original_filename)
        unique_id = uuid.uuid4().hex
        target = Path(ATTACHMENT_CONFIG.TEMP_UPLOAD_DIR) / f"{unique_id}_{safe_name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file_bytes)

        metadata = AttachmentMetadata(
            id=unique_id,
            filename=safe_name,
            mime_type=mime_type,
            size=len(file_bytes),
            extension=Path(safe_name).suffix.lower(),
            temp_path=str(target),
            is_image=mime_type.startswith("image/"),
            is_document=mime_type in {"application/pdf", "text/plain", "text/csv"},
            sanitized_name=safe_name,
            original_name=original_filename,
        )
        return metadata

    @staticmethod
    def cleanup_attachment(metadata: AttachmentMetadata) -> None:
        try:
            if metadata and metadata.temp_path:
                path = Path(metadata.temp_path)
                if path.exists():
                    path.unlink()
        except Exception:
            pass

    @staticmethod
    def cleanup_many(attachments: list[AttachmentMetadata]) -> None:
        for attachment in attachments:
            TemporaryAttachmentStorage.cleanup_attachment(attachment)
