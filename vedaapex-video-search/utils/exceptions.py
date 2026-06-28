"""
Custom exception classes for the application.
"""


class VedaApexException(Exception):
    """Base exception for VedaApex."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(VedaApexException):
    """Raised when validation fails."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class AuthenticationError(VedaApexException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class RateLimitError(VedaApexException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class ProviderError(VedaApexException):
    """Raised when provider returns an error."""

    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class CacheError(VedaApexException):
    """Raised when cache operation fails."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class NotFoundError(VedaApexException):
    """Raised when resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class InternalServerError(VedaApexException):
    """Raised for internal server errors."""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, status_code=500)
