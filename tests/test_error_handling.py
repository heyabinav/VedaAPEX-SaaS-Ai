"""
Tests for the global error handling and exception hierarchy.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AppException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    AIProviderError,
    DatabaseError,
    TimeoutError,
    InsufficientCreditsError,
    StorageError,
    FileTooLargeError,
)


class TestExceptionHierarchy:
    """Test that exceptions produce correct error responses."""

    def test_app_exception_defaults(self):
        exc = AppException()
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.to_dict()["success"] is False
        assert "timestamp" in exc.to_dict()

    def test_validation_error(self):
        exc = ValidationError("Bad input")
        assert exc.status_code == 400
        assert exc.error_code == "VALIDATION_ERROR"

    def test_authentication_error(self):
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_ERROR"

    def test_authorization_error(self):
        exc = AuthorizationError()
        assert exc.status_code == 403

    def test_not_found_error(self):
        exc = NotFoundError("User")
        assert exc.status_code == 404
        assert "User" in exc.message

    def test_rate_limit_error(self):
        exc = RateLimitError()
        assert exc.status_code == 429

    def test_ai_provider_error(self):
        exc = AIProviderError("OpenAI", "Rate limited")
        assert exc.status_code == 502
        assert "OpenAI" in exc.message
        assert exc.details["provider"] == "OpenAI"

    def test_database_error(self):
        exc = DatabaseError()
        assert exc.status_code == 503

    def test_timeout_error(self):
        exc = TimeoutError("Replicate", 30)
        assert exc.status_code == 504
        assert exc.details["timeout_seconds"] == 30

    def test_insufficient_credits_error(self):
        exc = InsufficientCreditsError(required=100, available=50)
        assert exc.status_code == 402
        assert exc.details["deficit"] == 50

    def test_storage_error(self):
        exc = StorageError()
        assert exc.status_code == 500

    def test_file_too_large_error(self):
        exc = FileTooLargeError(max_mb=150, actual_mb=200.5)
        assert exc.status_code == 413

    def test_to_dict_contains_all_fields(self):
        exc = AppException("test", "TEST_CODE", 418, {"key": "value"})
        d = exc.to_dict()
        assert d["success"] is False
        assert d["error_code"] == "TEST_CODE"
        assert d["message"] == "test"
        assert d["details"] == {"key": "value"}
        assert "timestamp" in d
        assert "request_id" in d
