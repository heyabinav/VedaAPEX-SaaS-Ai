"""
Custom exceptions - Legacy compatibility layer.

These exceptions inherit from the new centralized AppException hierarchy
in app.core.exceptions to maintain backward compatibility with existing code.
"""

from app.core.exceptions import (
    AppException as _AppException,
    ValidationError as _ValidationError,
    ProviderError as _ProviderError,
    NotFoundError as _NotFoundError,
    RateLimitError as _RateLimitError,
)


class VedaApexException(_AppException):
    """Base exception - backward compatible wrapper."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message=message, status_code=status_code, error_code="VEDAAPEX_ERROR")


class ValidationError(_ValidationError):
    """Validation error - backward compatible."""
    pass


class ProviderError(_ProviderError):
    """Provider error - backward compatible."""
    pass


class NotFoundError(_NotFoundError):
    """Not found error - backward compatible."""
    pass


class RateLimitError(_RateLimitError):
    """Rate limit error - backward compatible."""
    pass
