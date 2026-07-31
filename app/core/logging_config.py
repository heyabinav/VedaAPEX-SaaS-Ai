"""
Structured logging configuration.

Provides:
- JSON structured logs for production
- Human-readable logs for development
- File logging to api.log
- Sensitive value masking
- Request ID propagation
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


class SensitiveDataFilter(logging.Filter):
    """Masks sensitive values (API keys, tokens, passwords) in log output."""

    PATTERNS = [
        (re.compile(r'(api[_-]?key["\s:=]+)["\']?([A-Za-z0-9_\-\.]{8})[A-Za-z0-9_\-\.]*', re.IGNORECASE), r'\1\2****'),
        (re.compile(r'(token["\s:=]+)["\']?([A-Za-z0-9_\-\.]{8})[A-Za-z0-9_\-\.]*', re.IGNORECASE), r'\1\2****'),
        (re.compile(r'(password["\s:=]+)["\']?([^\s"\'}{,]+)', re.IGNORECASE), r'\1****'),
        (re.compile(r'(secret["\s:=]+)["\']?([A-Za-z0-9_\-\.]{8})[A-Za-z0-9_\-\.]*', re.IGNORECASE), r'\1\2****'),
        (re.compile(r'(va_live_[a-f0-9]{8})[a-f0-9]+', re.IGNORECASE), r'\1****'),
        (re.compile(r'(sk-[a-zA-Z0-9]{8})[a-zA-Z0-9]+', re.IGNORECASE), r'\1****'),
        (re.compile(r'(Bearer\s+[A-Za-z0-9_\-\.]{8})[A-Za-z0-9_\-\.]+', re.IGNORECASE), r'\1****'),
    ]

    def __init__(self, name: str = ""):
        super().__init__(name)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._mask_value(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._mask_value(a) if isinstance(a, str) else a for a in record.args
                )
        return True

    def _mask_value(self, value: str) -> str:
        for pattern, replacement in self.PATTERNS:
            value = pattern.sub(replacement, value)
        return value


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": self.formatException(record.exc_info),
            }

        for extra_field in ["user_id", "endpoint", "method", "status_code", "provider", "model", "duration_ms"]:
            if hasattr(record, extra_field):
                log_entry[extra_field] = getattr(record, extra_field)

        return json.dumps(log_entry, default=str)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable log format for development."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[1;31m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        base = f"{color}{timestamp} | {record.levelname:8s} | {record.name} | {record.getMessage()}{self.RESET}"

        if record.exc_info and record.exc_info[0]:
            base += f"\n{self.formatException(record.exc_info)}"

        return base


def setup_logging(env: str = "development") -> None:
    """Configure application-wide logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if env == "development" else logging.INFO)

    if env == "production":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(HumanReadableFormatter())

    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    file_handler = logging.FileHandler(log_dir / "api.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    file_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(file_handler)

    error_file_handler = logging.FileHandler(log_dir / "error.log", encoding="utf-8")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(JSONFormatter())
    error_file_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(error_file_handler)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
