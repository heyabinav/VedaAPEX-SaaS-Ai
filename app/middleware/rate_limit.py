import os
import time
import logging
import threading
from fastapi import Request, HTTPException

logger = logging.getLogger("media_backend")


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
                # Test connection
                self.redis_client.ping()
                self.redis_available = True
                logger.info("Redis Rate Limiter initialized successfully.")
            except Exception as e:
                logger.warning(
                    f"Could not connect to Redis for Rate Limiter. Fallback to in-memory active. Detail: {e}"
                )

    def is_rate_limited(self, identifier: str, limit: int = 60, window_seconds: int = 60) -> bool:
        """
        Validates whether an identifier (e.g. user_id or IP) exceeded a limit within the sliding window.
        """
        now = time.time()

        if self.redis_available:
            try:
                key = f"rate_limit:{identifier}"
                pipe = self.redis_client.pipeline()

                # Remove items older than window
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                # Count remaining items
                pipe.zcard(key)
                # Add current item
                pipe.zadd(key, {str(now): now})
                # Set key expiry to save Redis memory
                pipe.expire(key, window_seconds + 10)

                _, current_count, _, _ = pipe.execute()

                return current_count > limit
            except Exception as e:
                logger.error(
                    f"Redis rate limiting command failed: {e}. Running local memory fallback."
                )
                # Run local fallback

        # Thread-safe Local In-Memory Fallback
        with self.lock:
            if identifier not in self.local_cache:
                self.local_cache[identifier] = []

            # Filter times within current window
            timestamps = self.local_cache[identifier]
            cutoff = now - window_seconds
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]

            # Check limits
            is_limited = len(valid_timestamps) >= limit

            if not is_limited:
                valid_timestamps.append(now)

            self.local_cache[identifier] = valid_timestamps
            return is_limited


rate_limiter = RateLimiter()


def rate_limit(limit: int = 60, window: int = 60):
    """
    FastAPI endpoint dependency wrapper for Rate Limiting.
    Defaults to 60 requests per 60 seconds (1 minute).
    """

    async def dependency(request: Request):
        # Resolve identifier: API key header or client host IP
        api_key = request.headers.get("x-api-key")
        identifier = api_key if api_key else request.client.host

        if rate_limiter.is_rate_limited(identifier, limit=limit, window_seconds=window):
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down and try again later.",
            )

    return dependency
