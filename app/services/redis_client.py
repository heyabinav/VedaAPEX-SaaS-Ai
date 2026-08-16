"""
Redis connection pool and utilities for VedaApex.

This module provides a singleton Redis client with connection pooling
for efficient, non-blocking access to Redis from FastAPI.

Features:
- Lazy initialization (only connects when first used)
- Automatic connection pooling
- Graceful fallback if Redis is unavailable
- Health check functionality
- Async-first design with aioredis
"""

import asyncio
import json
import logging
from typing import Any, Optional
from urllib.parse import urlparse

try:
    import aioredis  # type: ignore
except ImportError:  # pragma: no cover
    aioredis = None

from redis.asyncio import Redis, ConnectionPool

from app.core.config import settings

logger = logging.getLogger("services.redis_client")


class RedisClient:
    """
    Singleton Redis client manager for VedaApex.
    
    Handles connection pooling, initialization, and graceful fallback.
    """

    _instance: Optional["RedisClient"] = None
    _redis: Optional[Redis] = None
    _pool: Optional[ConnectionPool] = None
    _available: bool = False

    def __new__(cls) -> "RedisClient":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls) -> None:
        """
        Initialize Redis connection pool.
        
        This is called during app startup to create the connection pool.
        If Redis is unavailable, sets _available = False and continues gracefully.
        """
        if cls._redis is not None:
            logger.debug("Redis already initialized")
            return

        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not configured; Redis chat memory disabled")
            cls._available = False
            return

        try:
            logger.info("Initializing Redis connection pool from %s...", cls._mask_redis_url(settings.REDIS_URL))
            
            # Create connection pool with sensible defaults
            cls._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=10,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE: 1 second
                    2: 1,  # TCP_KEEPINTVL: 1 second
                },
            )
            
            # Create Redis client from pool
            cls._redis = Redis(connection_pool=cls._pool, decode_responses=True)
            
            # Test connection
            await cls._redis.ping()
            logger.info("✓ Redis connected and ready")
            cls._available = True

        except Exception as e:
            logger.warning("Failed to connect to Redis: %s (will operate without cache)", e)
            cls._available = False
            cls._redis = None
            cls._pool = None

    @classmethod
    async def shutdown(cls) -> None:
        """
        Gracefully shutdown Redis connection pool.
        
        Called during app shutdown.
        """
        if cls._redis is not None:
            try:
                await cls._redis.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.warning("Error closing Redis connection: %s", e)
            finally:
                cls._redis = None
                cls._pool = None

    @classmethod
    def is_available(cls) -> bool:
        """Check if Redis is available and ready to use."""
        return cls._available

    @classmethod
    async def get(cls) -> Optional[Redis]:
        """
        Get the Redis client instance.
        
        Returns None if Redis is not available.
        Raises RuntimeError if called before initialize().
        """
        if cls._redis is None and not cls._available:
            # Try to initialize if not yet attempted
            await cls.initialize()
        return cls._redis if cls._available else None

    @classmethod
    async def health_check(cls) -> dict[str, Any]:
        """
        Check Redis health and return status info.
        
        Returns:
            Dict with status, latency, and error details if applicable.
        """
        if cls._redis is None:
            return {"status": "disconnected", "available": False}

        try:
            import time
            start = time.time()
            await cls._redis.ping()
            latency_ms = (time.time() - start) * 1000
            
            # Get info
            info = await cls._redis.info()
            return {
                "status": "healthy",
                "available": True,
                "latency_ms": round(latency_ms, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
            }
        except Exception as e:
            logger.warning("Redis health check failed: %s", e)
            return {"status": "error", "available": False, "error": str(e)}

    @staticmethod
    def _mask_redis_url(url: str) -> str:
        """
        Mask sensitive parts of Redis URL for logging.
        
        Replaces password with '*****' in URLs like redis://:password@host:port
        """
        try:
            parsed = urlparse(url)
            if parsed.password:
                return url.replace(parsed.password, "*****")
        except Exception:
            pass
        return url


async def get_redis_client() -> Optional[Redis]:
    """
    Dependency injection function for Redis client.
    
    Usage in FastAPI endpoints:
        @router.get("/example")
        async def example(redis: Optional[Redis] = Depends(get_redis_client)):
            if redis:
                await redis.set("key", "value")
    """
    return await RedisClient.get()
