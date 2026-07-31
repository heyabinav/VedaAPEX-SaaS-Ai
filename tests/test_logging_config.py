"""
Tests for the logging configuration and sensitive data masking.
"""

import logging

from app.core.logging_config import SensitiveDataFilter


class TestSensitiveDataFilter:
    def setup_method(self):
        self.filter = SensitiveDataFilter()

    def test_mask_api_key(self):
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Using api_key='sk-1234567890abcdef1234567890abcdef'",
            args=(), exc_info=None,
        )
        self.filter.filter(record)
        assert "1234567890abcdef" not in record.msg
        assert "****" in record.msg

    def test_mask_password(self):
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="password: mysecretpassword123",
            args=(), exc_info=None,
        )
        self.filter.filter(record)
        assert "mysecretpassword123" not in record.msg

    def test_mask_bearer_token(self):
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            args=(), exc_info=None,
        )
        self.filter.filter(record)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in record.msg

    def test_mask_va_live_key(self):
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Key: va_live_abc123def456ghi789jkl012mno345",
            args=(), exc_info=None,
        )
        self.filter.filter(record)
        # The full key should be masked - at least some chars hidden
        assert "****" in record.msg
        # The middle chars of the key should be hidden
        assert "def456ghi789jkl012mno345" not in record.msg

    def test_clean_message_unchanged(self):
        msg = "User logged in successfully"
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )
        self.filter.filter(record)
        assert record.msg == msg
