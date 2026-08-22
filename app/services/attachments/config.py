import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AttachmentConfig:
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "157286400"))
    MAX_FILES_PER_REQUEST: int = int(os.getenv("MAX_FILES_PER_REQUEST", "5"))
    TEMP_UPLOAD_DIR: str = os.getenv("TEMP_UPLOAD_DIR", os.path.join("tmp", "uploads"))
    ALLOWED_MIME_TYPES: set[str] = frozenset({
        "application/json",
        "application/octet-stream",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "application/pdf",
        "text/plain",
        "text/csv",
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "video/x-msvideo",
        "video/x-matroska",
    })
    ALLOWED_EXTENSIONS: set[str] = frozenset({
        ".csv",
        ".docx",
        ".gif",
        ".jpg",
        ".jpeg",
        ".json",
        ".mkv",
        ".mov",
        ".mp4",
        ".png",
        ".webp",
        ".pdf",
        ".pptx",
        ".txt",
        ".webm",
        ".xlsx",
    })
    MAX_IMAGE_DIMENSIONS: tuple[int, int] = (4096, 4096)
    MAX_DOCUMENT_CHARACTERS: int = 25000


ATTACHMENT_CONFIG = AttachmentConfig()
