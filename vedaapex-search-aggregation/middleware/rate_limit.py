"""Rate limiting middleware."""

import logging
from datetime import datetime, timedelta
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from config import config
from utils.helpers import helpers

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting per IP."""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        """Rate limit check."""
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip] if req_time > window_start
            ]

            if len(self.requests[client_ip]) >= self.max_requests:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": "RateLimitError",
                        "message": "Rate limit exceeded",
                        "status_code": 429,
                        "timestamp": helpers.get_timestamp(),
                    },
                )

            self.requests[client_ip].append(now)
        else:
            self.requests[client_ip] = [now]

        response = await call_next(request)
        return response
