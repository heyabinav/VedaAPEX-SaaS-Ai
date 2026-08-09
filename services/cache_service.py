"""Cache service for storing results."""

import json
import logging
import hashlib
from typing import Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract cache backend."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache."""
        pass


class InMemoryCache(CacheBackend):
    """In-memory LRU cache."""

    def __init__(self, max_size: int = 1000):
        """Initialize in-memory cache."""
        self.cache = {}
        self.max_size = max_size
        self.access_count = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get from memory cache."""
        if key in self.cache:
            self.access_count[key] = self.access_count.get(key, 0) + 1
            logger.debug(f"Cache HIT: {key}")
            return self.cache[key]

        logger.debug(f"Cache MISS: {key}")
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set in memory cache."""
        if len(self.cache) >= self.max_size:
            # Remove least accessed
            lru_key = min(self.access_count, key=self.access_count.get)
            del self.cache[lru_key]
            del self.access_count[lru_key]
            logger.debug(f"Cache evicted: {lru_key}")

        self.cache[key] = value
        self.access_count[key] = 0
        logger.debug(f"Cache SET: {key}")

    async def delete(self, key: str) -> None:
        """Delete from cache."""
        if key in self.cache:
            del self.cache[key]
            del self.access_count[key]

    async def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()
        self.access_count.clear()


class RedisCache(CacheBackend):
    """Redis cache backend."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis cache."""
        self.redis_url = redis_url
        self.redis = None

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            import aioredis

            self.redis = await aioredis.from_url(self.redis_url)
            await self.redis.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.redis = None
            raise

    async def get(self, key: str) -> Optional[Any]:
        """Get from Redis."""
        if not self.redis:
            logger.debug("Redis cache not connected, cache MISS")
            return None

        try:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"Redis HIT: {key}")
                return json.loads(value)
            logger.debug(f"Redis MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set in Redis."""
        if not self.redis:
            logger.warning("Redis cache not connected, skipping SET")
            return

        try:
            await self.redis.setex(key, ttl, json.dumps(value))
            logger.debug(f"Redis SET: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete from Redis."""
        if not self.redis:
            logger.warning("Redis cache not connected, skipping DELETE")
            return

        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    async def clear(self) -> None:
        """Clear Redis."""
        if not self.redis:
            logger.warning("Redis cache not connected, skipping CLEAR")
            return

        try:
            await self.redis.flushdb()
        except Exception as e:
            logger.error(f"Redis clear error: {e}")


class CacheService:
    """Unified cache service."""

    def __init__(
        self,
        backend_type: str = "memory",
        redis_url: str = None,
        enabled: bool = True,
    ):
        """Initialize cache service."""
        self.enabled = enabled
        self.backend_type = backend_type
        self.redis_url = redis_url
        self.backend: Optional[CacheBackend] = None

    async def initialize(self) -> None:
        """Initialize the cache backend."""
        if not self.enabled:
            self.backend = None
            logger.info("Cache is disabled")
            return

        if self.backend_type == "redis" and self.redis_url:
            self.backend = RedisCache(self.redis_url)
            try:
                await self.backend.connect()
            except Exception:
                logger.warning(
                    "Redis cache initialization failed; falling back to in-memory cache"
                )
                self.backend = InMemoryCache()
        else:
            self.backend = InMemoryCache()

    async def get(self, key: str) -> Optional[Any]:
        """Get from cache."""
        if not self.backend:
            return None
        return await self.backend.get(key)

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set in cache."""
        if not self.backend:
            return
        await self.backend.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        """Delete from cache."""
        if not self.backend:
            return
        await self.backend.delete(key)

    async def clear(self) -> None:
        """Clear cache."""
        if not self.backend:
            return
        await self.backend.clear()

    @staticmethod
    def generate_key(prefix: str, query: str, page: int = 1) -> str:
        """Generate cache key."""
        key_str = f"{prefix}:{query}:{page}"
        return hashlib.md5(key_str.encode()).hexdigest()
