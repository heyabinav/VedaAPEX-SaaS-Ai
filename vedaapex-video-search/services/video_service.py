"""
Video search service.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from providers.pexels_provider import PexelsProvider
from services.cache_service import cache_service
from utils.helpers import helpers
from utils.validators import validators
from schemas.responses import Pagination
from config import config

logger = logging.getLogger(__name__)


class VideoSearchService:
    """Service for video search."""

    def __init__(self, provider: PexelsProvider):
        """
        Initialize video search service.

        Args:
            provider: Pexels provider instance
        """
        self.provider = provider

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        sort: str = "latest",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Search for videos.

        Args:
            query: Search query
            page: Page number
            page_size: Results per page
            sort: Sort order
            use_cache: Whether to use cache

        Returns:
            Search results with pagination
        """
        # Validate input
        query = validators.validate_search_query(query)
        page, page_size = validators.validate_pagination(page, page_size, config.MAX_PAGE_SIZE)
        sort = validators.validate_sort_order(sort)

        logger.info(f"Searching videos: {query} (page {page}, size {page_size})")

        # Check cache
        cached_result = None
        if use_cache:
            cached_result = await cache_service.get_search_results(query, page, search_type="video")

        if cached_result:
            logger.info(f"Cache hit for: {query} (page {page})")
            cached_result["cached"] = True
            return cached_result

        logger.debug(f"Cache miss for: {query} (page {page})")

        # Fetch from provider
        try:
            raw_results = await self.provider.search_videos(
                query=query,
                page=page,
                per_page=page_size,
                sort=sort,
            )

            # Normalize results
            normalized = self._normalize_response(raw_results, query, page, page_size)

            # Cache results
            await cache_service.set_search_results(query, page, normalized, search_type="video")

            return normalized

        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            raise

    def _normalize_response(
        self,
        raw_response: Dict[str, Any],
        query: str,
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        """
        Normalize Pexels API response.

        Args:
            raw_response: Raw API response
            query: Search query
            page: Page number
            page_size: Results per page

        Returns:
            Normalized response
        """
        results = []

        # Extract videos
        videos = raw_response.get("videos", [])
        for video in videos:
            try:
                video_data = helpers.extract_video_metadata(video)
                results.append(video_data)
            except Exception as e:
                logger.warning(f"Failed to extract video metadata: {e}")
                continue

        # Calculate pagination
        total_results = raw_response.get("total_results", 0)
        has_next = raw_response.get("next_page") is not None

        pagination = Pagination(
            page=page,
            page_size=page_size,
            total_count=total_results,
            has_next=has_next,
        )

        return {
            "success": True,
            "query": query,
            "provider": "pexels",
            "results": results,
            "pagination": pagination.dict(),
            "timestamp": helpers.get_timestamp(),
            "cached": False,
        }

    async def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """
        Get search suggestions.

        Args:
            query: Partial query string
            limit: Maximum suggestions

        Returns:
            List of suggestions
        """
        # This would typically call a dedicated suggestion endpoint
        # For now, returning empty list
        logger.info(f"Getting suggestions for: {query}")
        return []
