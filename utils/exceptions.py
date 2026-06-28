"""Custom exceptions."""


class VedaApexException(Exception):
    """Base exception."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(VedaApexException):
    """Validation error."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class ProviderError(VedaApexException):
    """Provider error."""

    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class NotFoundError(VedaApexException):
    """Not found error."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class RateLimitError(VedaApexException):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)
