"""
Rate limiter middleware and dependency helpers.

The middleware provides server-wide protection with a sliding window limit.
The dependency is used by high-cost routes that need a tighter per-route cap.
"""

import logging
import os
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.middleware.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter for the whole app."""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._exempt_paths = {
            "/health",
            "/ready",
            "/api/v1/health",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
            "/docs",
            "/redoc",
            "/openapi.json",
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

    def _request_id(self, request: Request) -> str:
        return (
            getattr(request.state, "request_id", "")
            or request.headers.get("x-request-id", "")
            or uuid.uuid4().hex[:12]
        )

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in self._exempt_paths:
            return await call_next(request)

        client_id = self._client_identifier(request)
        if rate_limiter.is_rate_limited(
            client_id,
            limit=self.max_requests,
            window_seconds=self.window_seconds,
        ):
            retry_after = rate_limiter.get_retry_after(client_id, self.window_seconds)
            logger.warning("Rate limit exceeded for %s", client_id)
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down and try again later.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": self._request_id(request),
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

        response = await call_next(request)
        response.headers["X-Rate-Limit-Limit"] = str(self.max_requests)
        response.headers["X-Rate-Limit-Window"] = str(self.window_seconds)
        return response


class RateLimiter:
    """
    Sliding window rate limiter with Redis backend and thread-safe local in-memory fallback.
    """

    def __init__(self):
        self.redis_available = False
        self.redis_client = None
        self.local_cache = {}
        self.lock = threading.Lock()

        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                self.redis_available = True
                logger.info("Redis Rate Limiter initialized successfully.")
            except Exception as e:
                logger.warning(
                    "Could not connect to Redis for Rate Limiter. Fallback to in-memory active. Detail: %s",
                    e,
                )

    def is_rate_limited(self, identifier: str, limit: int = 60, window_seconds: int = 60) -> bool:
        """Check if an identifier has exceeded the rate limit."""
        now = time.time()

        if self.redis_available:
            try:
                key = f"rate_limit:{identifier}"
                pipe = self.redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.zcard(key)
                _, current_count = pipe.execute()
                if current_count >= limit:
                    return True

                pipe = self.redis_client.pipeline()
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, window_seconds + 10)
                pipe.execute()
                return False
            except Exception as e:
                logger.error("Redis rate limiting command failed: %s. Running local memory fallback.", e)

        # Thread-safe Local In-Memory Fallback
        with self.lock:
            if identifier not in self.local_cache:
                self.local_cache[identifier] = []

            timestamps = self.local_cache[identifier]
            cutoff = now - window_seconds
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]
            if len(valid_timestamps) >= limit:
                self.local_cache[identifier] = valid_timestamps
                return True

            valid_timestamps.append(now)
            self.local_cache[identifier] = valid_timestamps
            return False

    def get_retry_after(self, identifier: str, window_seconds: int = 60) -> int:
        """Get seconds until the rate limit resets."""
        if self.redis_available:
            try:
                key = f"rate_limit:{identifier}"
                oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_score = oldest[0][1]
                    return max(0, int(window_seconds - (time.time() - float(oldest_score))))
            except Exception as e:
                logger.error("Redis retry-after lookup failed: %s", e)

        with self.lock:
            timestamps = self.local_cache.get(identifier, [])
            if not timestamps:
                return 0
            oldest = min(timestamps)
            return max(0, int(window_seconds - (time.time() - oldest)))


rate_limiter = RateLimiter()


def rate_limit_dependency(limit: int = 60, window: int = 60):
    """
    FastAPI endpoint dependency for Rate Limiting.
    Returns structured JSON error when rate limited.
    """

    async def dependency(request: Request):
        api_key = request.headers.get("x-api-key")
        identifier = api_key if api_key else (request.client.host if request.client else "unknown")

        if rate_limiter.is_rate_limited(identifier, limit=limit, window_seconds=window):
            retry_after = rate_limiter.get_retry_after(identifier, window)

            raise HTTPException(
                status_code=429,
                detail={
                    "success": False,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down and try again later.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": getattr(request.state, "request_id", ""),
                    "details": {
                        "limit": limit,
                        "window_seconds": window,
                        "retry_after_seconds": retry_after,
                    },
                },
            )

    return dependency


# Backward compatibility alias
rate_limit = rate_limit_dependency
