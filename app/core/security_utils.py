"""
Security utilities: secret masking, filename sanitization, input validation.
"""

import hashlib
import os
import re
import secrets
import string
from pathlib import Path
from urllib.parse import urlparse


def mask_secret(value: str, visible_chars: int = 8) -> str:
    """Mask a secret string, showing only the first few characters."""
    if not value or len(value) <= visible_chars:
        return "****"
    return value[:visible_chars] + "*" * min(16, len(value) - visible_chars)


def mask_api_key(key: str) -> str:
    """Mask an API key for safe display in logs/UI."""
    if not key:
        return ""
    prefix = key[:8] if len(key) > 8 else key[:4]
    return f"{prefix}****"


def generate_request_id() -> str:
    """Generate a short unique request ID."""
    return secrets.token_hex(4)


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize a filename to prevent directory traversal and invalid characters.
    """
    if not filename:
        return "unnamed_file"

    filename = os.path.basename(filename)

    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)

    filename = re.sub(r'\.{2,}', '.', filename)

    filename = filename.strip('. ')

    if not filename:
        filename = "unnamed_file"

    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext

    return filename


def validate_url(url: str) -> bool:
    """Validate that a URL is well-formed and uses allowed schemes."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def is_safe_path(base_dir: str, requested_path: str) -> bool:
    """
    Prevent directory traversal attacks.
    Returns True if requested_path is within base_dir.
    """
    try:
        base = Path(base_dir).resolve()
        target = (base / requested_path).resolve()
        return str(target).startswith(str(base))
    except (ValueError, OSError):
        return False


def generate_secure_filename(extension: str = ".bin") -> str:
    """Generate a cryptographically secure random filename."""
    return f"{secrets.token_hex(16)}{extension}"


def hash_content(content: bytes) -> str:
    """Generate SHA-256 hash of content for deduplication."""
    return hashlib.sha256(content).hexdigest()


def extract_domain(url: str) -> str | None:
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".flv", ".wmv"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".wma"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".json"}


def get_file_category(filename: str) -> str:
    """Determine the file category based on extension."""
    ext = Path(filename).suffix.lower()
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return "images"
    elif ext in ALLOWED_VIDEO_EXTENSIONS:
        return "videos"
    elif ext in ALLOWED_AUDIO_EXTENSIONS:
        return "audio"
    elif ext in ALLOWED_DOCUMENT_EXTENSIONS:
        return "documents"
    return "other"


def get_content_type(filename: str) -> str:
    """Map file extension to MIME type."""
    ext = Path(filename).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
        ".mp4": "video/mp4", ".mov": "video/quicktime", ".avi": "video/x-msvideo",
        ".webm": "video/webm", ".mkv": "video/x-matroska",
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
        ".flac": "audio/flac", ".aac": "audio/aac",
        ".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".txt": "text/plain", ".json": "application/json",
    }
    return mime_map.get(ext, "application/octet-stream")
