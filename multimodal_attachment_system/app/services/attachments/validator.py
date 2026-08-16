import os
import re
import uuid
from pathlib import Path
from typing import BinaryIO

from .config import ATTACHMENT_CONFIG


class AttachmentValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def sanitize_filename(filename: str) -> str:
    if not filename:
        raise AttachmentValidationError("INVALID_FILENAME", "Filename is required.")
    safe = os.path.basename(filename)
    safe = safe.replace("\\", "/")
    safe = safe.strip()
    if not safe or safe in {".", ".."}:
        raise AttachmentValidationError("INVALID_FILENAME", "Invalid filename.")
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", safe)
    return safe


def validate_file_metadata(filename: str, mime_type: str, size: int) -> None:
    if size <= 0:
        raise AttachmentValidationError("EMPTY_FILE", "The uploaded file is empty.")
    if size > ATTACHMENT_CONFIG.MAX_FILE_SIZE:
        raise AttachmentValidationError("FILE_TOO_LARGE", "The uploaded file exceeds the maximum allowed size.")

    safe_name = sanitize_filename(filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in ATTACHMENT_CONFIG.ALLOWED_EXTENSIONS:
        raise AttachmentValidationError("UNSUPPORTED_FILE_TYPE", "This file type is not supported.")

    if mime_type not in ATTACHMENT_CONFIG.ALLOWED_MIME_TYPES:
        raise AttachmentValidationError("UNSUPPORTED_FILE_TYPE", "This file type is not supported.")


def build_unique_temp_path(filename: str) -> str:
    safe_name = sanitize_filename(filename)
    unique_id = uuid.uuid4().hex
    root = Path(ATTACHMENT_CONFIG.TEMP_UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    final_name = f"{unique_id}_{safe_name}"
    return str(root / final_name)


def ensure_safe_file_handle(file_obj: BinaryIO, filename: str) -> None:
    if file_obj is None:
        raise AttachmentValidationError("INVALID_REQUEST", "No file was uploaded.")
    validate_file_metadata(filename=filename, mime_type=(getattr(file_obj, "content_type", "") or ""), size=getattr(file_obj, "size", 0) or 0)
