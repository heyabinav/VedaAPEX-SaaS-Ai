"""
Rate limiter middleware with structured error responses.

Returns consistent JSON error format when rate limited:
{
  "success": false,
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "...",
  "timestamp": "...",
  "request_id": "..."
}
"""

import os
import time
import logging
import threading
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.middleware.rate_limit")


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
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, window_seconds + 10)
                _, current_count, _, _ = pipe.execute()
                return current_count > limit
            except Exception as e:
                logger.error("Redis rate limiting command failed: %s. Running local memory fallback.", e)

        # Thread-safe Local In-Memory Fallback
        with self.lock:
            if identifier not in self.local_cache:
                self.local_cache[identifier] = []

            timestamps = self.local_cache[identifier]
            cutoff = now - window_seconds
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]
            is_limited = len(valid_timestamps) >= limit

            if not is_limited:
                valid_timestamps.append(now)

            self.local_cache[identifier] = valid_timestamps
            return is_limited

    def get_retry_after(self, identifier: str, window_seconds: int = 60) -> int:
        """Get seconds until the rate limit resets."""
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

            request_id = getattr(request.state, "request_id", "")

            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down and try again later.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                    "details": {
                        "limit": limit,
                        "window_seconds": window,
                        "retry_after_seconds": retry_after,
                    },
                },
                headers={"Retry-After": str(retry_after), "X-Rate-Limit-Limit": str(limit)},
            )

    return dependency


# Backward compatibility alias
rate_limit = rate_limit_dependency
