"""
Security middleware - adds security headers.
"""

import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Add security headers to response.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        """
        Check rate limit for request.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for health check
        if request.url.path == "/api/v1/health":
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip] if req_time > window_start
            ]

            # Check limit
            if len(self.requests[client_ip]) >= self.max_requests:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": "RateLimitError",
                        "message": "Rate limit exceeded. Maximum 60 requests per minute.",
                        "status_code": 429,
                    },
                )

            # Add new request
            self.requests[client_ip].append(now)
        else:
            self.requests[client_ip] = [now]

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            self.max_requests - len(self.requests.get(client_ip, []))
        )

        return response
