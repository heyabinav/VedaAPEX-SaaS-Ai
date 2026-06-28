"""
Video Search Service - Orchestrates video search with caching
"""

import logging
from typing import Dict, Any

from services.provider_manager import ProviderManager
from utils.helpers import helpers
from utils.validators import validators
from config import config

logger = logging.getLogger(__name__)


class VideoSearchService:
    """Video search service with multi-provider support."""

    def __init__(self, provider_manager: ProviderManager):
        """Initialize service."""
        self.provider_manager = provider_manager
        self.cache = {}  # Simple in-memory cache

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = None,
    ) -> Dict[str, Any]:
        """Search for videos."""
        # Validate input
        query = validators.validate_query(query)
        page, page_size = validators.validate_pagination(page, page_size)

        logger.info(f"Video search: {query} (page {page})")

        # Generate cache key
        cache_key = helpers.generate_cache_key("video", query, page)

        # Check cache
        if config.CACHE_ENABLED and cache_key in self.cache:
            logger.info(f"Cache hit: {query}")
            cached = self.cache[cache_key].copy()
            cached["cached"] = True
            return cached

        logger.debug(f"Cache miss: {query}")

        # Search
        try:
            results = await self.provider_manager.search_videos(query, page, page_size)

            # Build response
            response = {
                "success": True,
                "provider": "multi-provider",
                "query": query,
                "results": results,
                "pagination": {
                    "page": page,
                    "page_size": page_size or config.DEFAULT_PAGE_SIZE,
                    "has_next": len(results) == (page_size or config.DEFAULT_PAGE_SIZE),
                },
                "timestamp": helpers.get_timestamp(),
                "cached": False,
            }

            # Cache result
            if config.CACHE_ENABLED:
                self.cache[cache_key] = response.copy()
                self.cache[cache_key]["cached"] = False
                logger.debug(f"Cached: {cache_key}")

            return response

        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            raise
