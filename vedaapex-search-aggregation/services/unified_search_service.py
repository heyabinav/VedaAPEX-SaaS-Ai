"""Unified search service."""

import logging
from typing import Dict
from services.cache_service import CacheService
from services.intelligent_router import router
from providers.provider_manager import ProviderManager
from utils.helpers import helpers
from utils.ranking import ranking_system
from utils.validators import validators
from config import config

logger = logging.getLogger(__name__)


class UnifiedSearchService:
    """Unified search across multiple providers."""

    def __init__(self, provider_manager: ProviderManager, cache: CacheService):
        """Initialize service."""
        self.pm = provider_manager
        self.cache = cache

    async def search(
        self,
        query: str,
        media_type: str = "image",
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """
        Perform unified search with intelligent routing.

        Auto-selects best provider based on query content.
        Falls back to secondary providers if primary has issues.
        """
        # Validate inputs
        query = validators.validate_query(query)
        media_type = validators.validate_media_type(media_type)
        page, page_size = validators.validate_pagination(page, page_size)

        # Generate cache key
        cache_key = CacheService.generate_key(f"search:{media_type}", query, page)

        # Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for '{query}'")
            cached["cached"] = True
            return cached

        # Get routing decision
        primary_provider, fallback_providers = router.route_query(query)

        # Build provider list (primary + fallbacks)
        provider_list = [primary_provider] + fallback_providers

        logger.info(
            f"Routing '{query}': primary={primary_provider}, " f"fallbacks={fallback_providers}"
        )

        # Search all providers concurrently
        provider_results = await self.pm.multi_search(
            provider_list, query, media_type, page, page_size
        )

        # Convert provider responses to result objects
        all_results = []
        for provider, items in provider_results.items():
            for item in items:
                result = self._normalize_result(item, provider, media_type)
                all_results.append(result)

        # Deduplicate and rank
        all_results = ranking_system.deduplicate_results(all_results)
        all_results = ranking_system.rank_results(all_results)
        all_results = all_results[: config.MAX_RESULTS]

        # Build response
        response = {
            "success": True,
            "query": query,
            "selected_provider": primary_provider,
            "fallback_providers": fallback_providers,
            "results": all_results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "has_next": len(all_results) >= page_size,
            },
            "timestamp": helpers.get_timestamp(),
            "cached": False,
        }

        # Cache response
        await self.cache.set(cache_key, response, config.CACHE_TTL)

        logger.info(f"Unified search complete: {len(all_results)} results")
        return response

    @staticmethod
    def _normalize_result(item: Dict, provider: str, media_type: str) -> Dict:
        """Normalize result from any provider."""
        # Extract common fields - adapt based on provider response format
        normalized = {
            "title": item.get("title") or item.get("description", "Untitled"),
            "description": item.get("description", ""),
            "media_type": media_type,
            "provider": provider,
            "image_url": item.get("image_url") or item.get("src", {}).get("medium"),
            "video_url": item.get("video_url") or item.get("video_file", {}).get("link"),
            "thumbnail_url": item.get("thumbnail_url") or item.get("src", {}).get("small"),
            "source_url": item.get("source_url") or item.get("url", ""),
        }
        return normalized
