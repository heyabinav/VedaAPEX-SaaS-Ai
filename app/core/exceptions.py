"""
Centralized exception hierarchy for the entire application.

Every exception maps to a consistent JSON response:
{
  "success": false,
  "error_code": "...",
  "message": "...",
  "timestamp": "...",
  "request_id": "..."
}
"""

import uuid
from datetime import datetime, timezone


class AppException(Exception):
    """Base application exception with structured error response."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.request_id = str(uuid.uuid4())[:8]
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "details": self.details if self.details else None,
        }


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", details: dict | None = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
        )


class AuthorizationError(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
        )


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            status_code=404,
        )


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
        )


class AIProviderError(AppException):
    def __init__(self, provider: str = "unknown", message: str = "AI provider error"):
        super().__init__(
            message=f"[{provider}] {message}",
            error_code="AI_PROVIDER_ERROR",
            status_code=502,
            details={"provider": provider},
        )


class ProviderError(AppException):
    def __init__(self, message: str = "Provider error", provider: str = "unknown"):
        super().__init__(
            message=message,
            error_code="AI_PROVIDER_ERROR",
            status_code=502,
            details={"provider": provider},
        )


class DatabaseError(AppException):
    def __init__(self, message: str = "Database service unavailable"):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=503,
        )


class TimeoutError(AppException):
    def __init__(self, service: str = "upstream", timeout_seconds: int = 0):
        super().__init__(
            message=f"{service} request timed out after {timeout_seconds}s",
            error_code="TIMEOUT_ERROR",
            status_code=504,
            details={"service": service, "timeout_seconds": timeout_seconds},
        )


class InsufficientCreditsError(AppException):
    def __init__(self, required: int = 0, available: int = 0):
        super().__init__(
            message="Insufficient credits",
            error_code="INSUFFICIENT_CREDITS",
            status_code=402,
            details={
                "required": required,
                "available": available,
                "deficit": required - available,
            },
        )


class StorageError(AppException):
    def __init__(self, message: str = "Storage operation failed"):
        super().__init__(
            message=message,
            error_code="STORAGE_ERROR",
            status_code=500,
        )


class FileTooLargeError(AppException):
    def __init__(self, max_mb: int = 150, actual_mb: float = 0):
        super().__init__(
            message=f"File too large. Maximum {max_mb}MB, received {actual_mb:.1f}MB",
            error_code="FILE_TOO_LARGE",
            status_code=413,
            details={"max_mb": max_mb, "actual_mb": actual_mb},
        )


class InvalidFileError(AppException):
    def __init__(self, message: str = "Invalid file format"):
        super().__init__(
            message=message,
            error_code="INVALID_FILE",
            status_code=400,
        )


# Persistent User Skill & Hugging Face Storage Exceptions
class SkillNotFound(AppException):
    def __init__(self, message: str = "Skill not found"):
        super().__init__(message=message, error_code="SKILL_NOT_FOUND", status_code=404)


class SkillAlreadyExists(AppException):
    def __init__(self, message: str = "Skill already exists"):
        super().__init__(message=message, error_code="SKILL_ALREADY_EXISTS", status_code=409)


class InvalidSkillName(AppException):
    def __init__(self, message: str = "Invalid skill name"):
        super().__init__(message=message, error_code="INVALID_SKILL_NAME", status_code=400)


class InvalidSkillLevel(AppException):
    def __init__(self, message: str = "Invalid skill level. Allowed: beginner, intermediate, advanced, expert"):
        super().__init__(message=message, error_code="INVALID_SKILL_LEVEL", status_code=400)


class InvalidConfidence(AppException):
    def __init__(self, message: str = "Invalid confidence score. Must be between 0.0 and 1.0"):
        super().__init__(message=message, error_code="INVALID_CONFIDENCE", status_code=400)


class SkillUnauthorized(AppException):
    def __init__(self, message: str = "Not authorized to access this skill"):
        super().__init__(message=message, error_code="SKILL_UNAUTHORIZED", status_code=403)


class InvalidUserId(AppException):
    def __init__(self, message: str = "Invalid user ID"):
        super().__init__(message=message, error_code="INVALID_USER_ID", status_code=400)


class HFStorageUnavailable(AppException):
    def __init__(self, message: str = "Hugging Face storage service unavailable"):
        super().__init__(message=message, error_code="HF_STORAGE_UNAVAILABLE", status_code=503)


class HFAuthenticationFailed(AppException):
    def __init__(self, message: str = "Hugging Face authentication failed"):
        super().__init__(message=message, error_code="HF_AUTHENTICATION_FAILED", status_code=401)


class HFPermissionDenied(AppException):
    def __init__(self, message: str = "Hugging Face permission denied"):
        super().__init__(message=message, error_code="HF_PERMISSION_DENIED", status_code=403)


class HFUploadFailed(AppException):
    def __init__(self, message: str = "Failed to upload file to Hugging Face"):
        super().__init__(message=message, error_code="HF_UPLOAD_FAILED", status_code=502)


class HFDownloadFailed(AppException):
    def __init__(self, message: str = "Failed to download file from Hugging Face"):
        super().__init__(message=message, error_code="HF_DOWNLOAD_FAILED", status_code=502)


class HFDeleteFailed(AppException):
    def __init__(self, message: str = "Failed to delete file from Hugging Face"):
        super().__init__(message=message, error_code="HF_DELETE_FAILED", status_code=502)
