"""MCP-specific exception classes.

All exceptions extend the application's AppException base so they get
structured JSON responses via the centralized error handlers.
Never expose Python stack traces or internal details to users.
"""

from app.core.exceptions import AppException


class MCPError(AppException):
    """Base class for all MCP-related errors."""

    def __init__(
        self,
        message: str = "MCP operation failed",
        error_code: str = "MCP_ERROR",
        status_code: int = 502,
        details: dict | None = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class MCPInvalidURL(MCPError):
    def __init__(self, message: str = "Invalid MCP server URL"):
        super().__init__(message=message, error_code="MCP_INVALID_URL", status_code=400)


class MCPSSRFBlocked(MCPError):
    def __init__(self, message: str = "MCP URL blocked by security policy"):
        super().__init__(message=message, error_code="MCP_SSRF_BLOCKED", status_code=403)


class MCPConnectionFailed(MCPError):
    def __init__(self, message: str = "Failed to connect to MCP server"):
        super().__init__(message=message, error_code="MCP_CONNECTION_FAILED", status_code=502)


class MCPTimeout(MCPError):
    def __init__(self, message: str = "MCP server request timed out"):
        super().__init__(message=message, error_code="MCP_TIMEOUT", status_code=504)


class MCPProtocolError(MCPError):
    def __init__(self, message: str = "MCP protocol error"):
        super().__init__(message=message, error_code="MCP_PROTOCOL_ERROR", status_code=502)


class MCPAuthRequired(MCPError):
    def __init__(self, message: str = "MCP server requires authentication"):
        super().__init__(message=message, error_code="MCP_AUTH_REQUIRED", status_code=401)


class MCPOAuthDiscoveryFailed(MCPError):
    def __init__(self, message: str = "Failed to discover OAuth configuration"):
        super().__init__(message=message, error_code="MCP_OAUTH_DISCOVERY_FAILED", status_code=502)


class MCPOAuthStateInvalid(MCPError):
    def __init__(self, message: str = "Invalid or expired OAuth state"):
        super().__init__(message=message, error_code="MCP_OAUTH_STATE_INVALID", status_code=400)


class MCPOAuthDenied(MCPError):
    def __init__(self, message: str = "OAuth authorization was denied"):
        super().__init__(message=message, error_code="MCP_OAUTH_DENIED", status_code=403)


class MCPTokenExchangeFailed(MCPError):
    def __init__(self, message: str = "OAuth token exchange failed"):
        super().__init__(message=message, error_code="MCP_TOKEN_EXCHANGE_FAILED", status_code=502)


class MCPTokenRefreshFailed(MCPError):
    def __init__(self, message: str = "OAuth token refresh failed"):
        super().__init__(message=message, error_code="MCP_TOKEN_REFRESH_FAILED", status_code=502)


class MCPToolNotFound(MCPError):
    def __init__(self, message: str = "MCP tool not found"):
        super().__init__(message=message, error_code="MCP_TOOL_NOT_FOUND", status_code=404)


class MCPToolCallFailed(MCPError):
    def __init__(self, message: str = "MCP tool call failed"):
        super().__init__(message=message, error_code="MCP_TOOL_CALL_FAILED", status_code=502)


class MCPConnectorNotFound(MCPError):
    def __init__(self, message: str = "MCP connector not found"):
        super().__init__(message=message, error_code="MCP_CONNECTOR_NOT_FOUND", status_code=404)


class MCPConnectorUnauthorized(MCPError):
    def __init__(self, message: str = "Not authorized to access this connector"):
        super().__init__(message=message, error_code="MCP_CONNECTOR_UNAUTHORIZED", status_code=403)


class MCPReauthRequired(MCPError):
    def __init__(self, message: str = "Re-authorization required"):
        super().__init__(message=message, error_code="MCP_REAUTH_REQUIRED", status_code=401)
