"""
Cache service.
"""

import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from config import config

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract cache backend."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class InMemoryCache(CacheBackend):
    """In-memory cache with TTL."""

    def __init__(self, max_size: int = 1000):
        """Initialize in-memory cache."""
        self.max_size = max_size
        self.cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            return None

        value, expiry_time = self.cache[key]

        # Check if expired
        if datetime.utcnow() > expiry_time:
            del self.cache[key]
            return None

        return value

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in cache."""
        expiry_time = datetime.utcnow() + timedelta(seconds=ttl)

        # LRU eviction
        if len(self.cache) >= self.max_size:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k][1],
            )
            del self.cache[oldest_key]
            logger.debug(f"Evicted cache entry: {oldest_key}")

        self.cache[key] = (value, expiry_time)
        logger.debug(f"Cached: {key} (TTL: {ttl}s)")

        return True

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    async def clear(self) -> bool:
        """Clear all cache."""
        self.cache.clear()
        logger.info("Cache cleared")
        return True

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        expired_count = sum(1 for _, expiry in self.cache.values() if datetime.utcnow() > expiry)

        return {
            "type": "in_memory",
            "total_entries": len(self.cache),
            "max_size": self.max_size,
            "expired_entries": expired_count,
        }


class RedisCache(CacheBackend):
    """Redis cache backend."""

    def __init__(self, redis_url: str):
        """Initialize Redis cache."""
        self.redis_url = redis_url
        self.client = None

    async def connect(self):
        """Connect to Redis."""
        try:
            import redis.asyncio as redis

            self.client = await redis.from_url(self.redis_url)
            await self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            import json

            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in cache."""
        try:
            import json

            await self.client.setex(key, ttl, json.dumps(value))
            logger.debug(f"Cached: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cache."""
        try:
            await self.client.flushdb()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            info = await self.client.info()
            return {
                "type": "redis",
                "used_memory": info.get("used_memory_human"),
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"type": "redis", "error": str(e)}


class CacheService:
    """Cache service with unified interface."""

    def __init__(self):
        """Initialize cache service."""
        self.backend: Optional[CacheBackend] = None
        self.enabled = config.CACHE_ENABLED

    async def initialize(self):
        """Initialize cache backend."""
        if not self.enabled:
            logger.info("Cache is disabled")
            return

        try:
            if config.CACHE_TYPE == "redis":
                self.backend = RedisCache(config.REDIS_URL)
                await self.backend.connect()
            else:
                self.backend = InMemoryCache(max_size=config.CACHE_MAX_SIZE)
                logger.info("Using in-memory cache")
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            self.backend = InMemoryCache(max_size=config.CACHE_MAX_SIZE)

    async def get(self, key: str) -> Optional[Any]:
        """Get from cache."""
        if not self.enabled or not self.backend:
            return None
        return await self.backend.get(key)

    async def set(self, key: str, value: Any) -> bool:
        """Set in cache."""
        if not self.enabled or not self.backend:
            return False
        return await self.backend.set(key, value, config.CACHE_TTL)

    async def delete(self, key: str) -> bool:
        """Delete from cache."""
        if not self.backend:
            return False
        return await self.backend.delete(key)

    async def clear(self) -> bool:
        """Clear cache."""
        if not self.backend:
            return False
        return await self.backend.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.backend:
            return {"enabled": False}

        stats = await self.backend.get_stats()
        stats["enabled"] = self.enabled
        return stats


cache_service = CacheService()
