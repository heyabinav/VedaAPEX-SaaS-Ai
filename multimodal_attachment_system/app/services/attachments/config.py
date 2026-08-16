import os
from dataclasses import dataclass
from typing import Set


@dataclass(frozen=True)
class AttachmentConfig:
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))
    MAX_FILES_PER_REQUEST: int = int(os.getenv("MAX_FILES_PER_REQUEST", "5"))
    TEMP_UPLOAD_DIR: str = os.getenv("TEMP_UPLOAD_DIR", os.path.join("tmp", "uploads"))
    ALLOWED_MIME_TYPES: Set[str] = frozenset({
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "text/plain",
        "text/csv",
    })
    ALLOWED_EXTENSIONS: Set[str] = frozenset({
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".pdf",
        ".txt",
        ".csv",
    })
    MAX_IMAGE_DIMENSIONS: tuple[int, int] = (4096, 4096)
    MAX_DOCUMENT_CHARACTERS: int = 25000


ATTACHMENT_CONFIG = AttachmentConfig()
