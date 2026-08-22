import os
import re
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .config import ATTACHMENT_CONFIG


class AttachmentValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def sanitize_filename(filename: str) -> str:
    if not filename:
        raise AttachmentValidationError("INVALID_FILENAME", "Filename is required.")
    safe = os.path.basename(filename).replace("\\", "/").strip()
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
    if mime_type and mime_type not in ATTACHMENT_CONFIG.ALLOWED_MIME_TYPES:
        raise AttachmentValidationError("UNSUPPORTED_FILE_TYPE", "This file type is not supported.")


def validate_image_content(file_bytes: bytes, mime_type: str) -> None:
    if not (mime_type or "").startswith("image/"):
        return

    try:
        with Image.open(BytesIO(file_bytes)) as image:
            image.verify()
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise AttachmentValidationError("CORRUPTED_IMAGE", "The uploaded image could not be read.") from exc

    max_width, max_height = ATTACHMENT_CONFIG.MAX_IMAGE_DIMENSIONS
    if width > max_width or height > max_height:
        raise AttachmentValidationError(
            "IMAGE_DIMENSIONS_TOO_LARGE",
            f"Image dimensions exceed the maximum allowed size of {max_width}x{max_height}.",
        )


def build_unique_temp_path(filename: str) -> str:
    safe_name = sanitize_filename(filename)
    unique_id = uuid.uuid4().hex
    root = Path(ATTACHMENT_CONFIG.TEMP_UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return str(root / f"{unique_id}_{safe_name}")
