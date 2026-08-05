"""Rate limiting middleware."""

import logging
import threading
import time
from collections import deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from utils.helpers import helpers

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting per client identifier with an in-memory sliding window."""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._exempt_paths = {
            "/health",
            "/api/v1/health",
            "/docs",
            "/api/v1/docs",
            "/redoc",
            "/api/v1/redoc",
            "/openapi.json",
            "/api/v1/openapi.json",
            "/favicon.ico",
        }

    def _client_identifier(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            first_hop = forwarded_for.split(",")[0].strip()
            if first_hop:
                return first_hop

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        if request.client and request.client.host:
            return request.client.host

        return "unknown"

    def _cleanup(self, now: float) -> None:
        cutoff = now - self.window_seconds
        empty_keys = []
        for identifier, timestamps in self._requests.items():
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if not timestamps:
                empty_keys.append(identifier)

        for identifier in empty_keys:
            self._requests.pop(identifier, None)

    async def dispatch(self, request: Request, call_next):
        """Rate limit check."""
        if request.method == "OPTIONS" or request.url.path in self._exempt_paths:
            return await call_next(request)

        client_id = self._client_identifier(request)
        now = time.monotonic()

        with self._lock:
            bucket = self._requests.setdefault(client_id, deque())
            cutoff = now - self.window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                logger.warning("Rate limit exceeded for %s", client_id)
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": "RateLimitError",
                        "message": "Rate limit exceeded",
                        "status_code": 429,
                        "timestamp": helpers.get_timestamp(),
                        "details": {
                            "limit": self.max_requests,
                            "window_seconds": self.window_seconds,
                            "retry_after_seconds": retry_after,
                        },
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-Rate-Limit-Limit": str(self.max_requests),
                        "X-Rate-Limit-Window": str(self.window_seconds),
                    },
                )

            bucket.append(now)

            if len(self._requests) > 1024:
                self._cleanup(now)

        response = await call_next(request)
        remaining = max(0, self.max_requests - len(self._requests.get(client_id, ())))
        response.headers["X-Rate-Limit-Limit"] = str(self.max_requests)
        response.headers["X-Rate-Limit-Remaining"] = str(remaining)
        response.headers["X-Rate-Limit-Window"] = str(self.window_seconds)
        return response
