import uuid
from pathlib import Path

from .config import ATTACHMENT_CONFIG
from .models import AttachmentMetadata
from .validator import sanitize_filename


class TemporaryAttachmentStorage:
    DOCUMENT_MIME_TYPES = {
        "application/json",
        "application/pdf",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/csv",
        "text/plain",
    }

    @staticmethod
    def ensure_root() -> str:
        root = Path(ATTACHMENT_CONFIG.TEMP_UPLOAD_DIR)
        root.mkdir(parents=True, exist_ok=True)
        return str(root)

    @staticmethod
    def save_upload(file_bytes: bytes, original_filename: str, mime_type: str) -> AttachmentMetadata:
        safe_name = sanitize_filename(original_filename)
        extension = Path(safe_name).suffix.lower()
        unique_id = uuid.uuid4().hex
        target = Path(ATTACHMENT_CONFIG.TEMP_UPLOAD_DIR) / f"{unique_id}_{safe_name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file_bytes)

        return AttachmentMetadata(
            id=unique_id,
            filename=safe_name,
            mime_type=mime_type,
            size=len(file_bytes),
            extension=extension,
            temp_path=str(target),
            is_image=mime_type.startswith("image/") or extension in {".jpg", ".jpeg", ".png", ".webp", ".gif"},
            is_document=mime_type in TemporaryAttachmentStorage.DOCUMENT_MIME_TYPES or extension in {".csv", ".docx", ".json", ".pdf", ".pptx", ".txt", ".xlsx"},
            sanitized_name=safe_name,
            original_name=original_filename,
            extra={
                "is_video": mime_type.startswith("video/") or extension in {".mp4", ".mov", ".webm", ".avi", ".mkv"},
            },
        )

    @staticmethod
    def cleanup_attachment(metadata: AttachmentMetadata | None) -> None:
        if not metadata or not metadata.temp_path:
            return
        try:
            path = Path(metadata.temp_path)
            if path.exists():
                path.unlink()
        except Exception:
            pass

    @staticmethod
    def cleanup_many(attachments: list[AttachmentMetadata]) -> None:
        for attachment in attachments:
            TemporaryAttachmentStorage.cleanup_attachment(attachment)
