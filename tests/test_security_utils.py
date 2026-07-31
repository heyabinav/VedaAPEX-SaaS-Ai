"""
Tests for security utilities: filename sanitization, secret masking, path safety.
"""

import pytest

from app.core.security_utils import (
    mask_secret,
    mask_api_key,
    sanitize_filename,
    validate_url,
    is_safe_path,
    generate_secure_filename,
    get_file_category,
    get_content_type,
)


class TestSecretMasking:
    def test_mask_secret_short(self):
        assert mask_secret("abc") == "****"

    def test_mask_secret_long(self):
        result = mask_secret("sk-1234567890abcdef")
        assert result.startswith("sk-1234")
        assert "****" in result
        # Content after visible chars should be masked
        assert "567890abcdef" not in result

    def test_mask_api_key(self):
        result = mask_api_key("va_live_abc123def456ghi789")
        assert result.startswith("va_live_")
        assert "****" in result

    def test_mask_api_key_empty(self):
        assert mask_api_key("") == ""


class TestFilenameSanitization:
    def test_normal_filename(self):
        assert sanitize_filename("photo.jpg") == "photo.jpg"

    def test_traversal_attack(self):
        result = sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_special_characters(self):
        result = sanitize_filename('file<>"name|?*.jpg')
        for ch in '<>:"/\\|?*':
            assert ch not in result

    def test_empty_filename(self):
        assert sanitize_filename("") == "unnamed_file"

    def test_only_dots(self):
        result = sanitize_filename("...")
        assert result != "..."

    def test_long_filename(self):
        long_name = "a" * 300 + ".jpg"
        result = sanitize_filename(long_name, max_length=200)
        assert len(result) <= 200


class TestURLValidation:
    def test_valid_https(self):
        assert validate_url("https://example.com/path") is True

    def test_valid_http(self):
        assert validate_url("http://localhost:8000/api") is True

    def test_invalid_scheme(self):
        assert validate_url("ftp://example.com") is False

    def test_empty_url(self):
        assert validate_url("") is False

    def test_no_netloc(self):
        assert validate_url("https://") is False


class TestPathSafety:
    def test_safe_path(self):
        assert is_safe_path("/uploads", "file.jpg") is True

    def test_traversal_attack(self):
        assert is_safe_path("/uploads", "../../etc/passwd") is False

    def test_subdirectory(self):
        assert is_safe_path("/uploads", "subdir/file.jpg") is True


class TestFileCategory:
    def test_image(self):
        assert get_file_category("photo.jpg") == "images"
        assert get_file_category("image.PNG") == "images"
        assert get_file_category("anim.webp") == "images"

    def test_video(self):
        assert get_file_category("clip.mp4") == "videos"
        assert get_file_category("movie.mov") == "videos"

    def test_audio(self):
        assert get_file_category("song.mp3") == "audio"
        assert get_file_category("voice.wav") == "audio"

    def test_document(self):
        assert get_file_category("report.pdf") == "documents"
        assert get_file_category("data.xlsx") == "documents"

    def test_unknown(self):
        assert get_file_category("file.xyz") == "other"


class TestContentType:
    def test_jpeg(self):
        assert get_content_type("photo.jpg") == "image/jpeg"

    def test_png(self):
        assert get_content_type("image.png") == "image/png"

    def test_mp4(self):
        assert get_content_type("video.mp4") == "video/mp4"

    def test_unknown(self):
        assert get_content_type("file.xyz") == "application/octet-stream"


class TestSecureFilename:
    def test_has_extension(self):
        result = generate_secure_filename(".jpg")
        assert result.endswith(".jpg")
        assert len(result) > 10

    def test_unique(self):
        names = {generate_secure_filename() for _ in range(100)}
        assert len(names) == 100
