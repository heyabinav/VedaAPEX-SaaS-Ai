"""
Video search service.
"""

import logging
from typing import Dict, Any

from providers.wikimedia_provider import WikimediaProvider
from services.cache_service import cache_service
from utils.helpers import helpers
from utils.validators import validators
from schemas.responses import Pagination
from config import config

logger = logging.getLogger(__name__)


class VideoSearchService:
    """Video search service."""

    def __init__(self, provider: WikimediaProvider):
        """Initialize service."""
        self.provider = provider

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Search for videos."""
        # Validate input
        query = validators.validate_query(query)
        page, page_size = validators.validate_pagination(page, page_size)

        logger.info(f"Video search: {query} (page {page})")

        # Check cache
        cache_key = helpers.generate_cache_key("video", query, page)

        if use_cache:
            cached = await cache_service.get(cache_key)
            if cached:
                logger.info(f"Cache hit: {query}")
                cached["cached"] = True
                return cached

        logger.debug(f"Cache miss: {query}")

        # Search
        try:
            offset = (page - 1) * page_size

            # Search files
            raw_results = await self.provider.search_videos(
                query=query,
                limit=page_size,
                offset=offset,
            )

            # Extract file titles
            file_titles = []
            search_results = raw_results.get("query", {}).get("search", [])

            for result in search_results:
                title = result.get("title", "")
                # Filter videos
                if helpers.is_video(title):
                    file_titles.append(title)

            # Get detailed file info
            file_details = {}
            if file_titles:
                details_response = await self.provider.get_file_info(file_titles)
                file_details = details_response.get("query", {}).get("pages", {})

            # Normalize results
            results = []
            for title in file_titles:
                # Find page info
                page_id = None
                for pid, pdata in file_details.items():
                    if pdata.get("title") == title:
                        page_id = pid
                        break

                if page_id and page_id in file_details:
                    metadata = helpers.extract_video_metadata(file_details[page_id])
                    if metadata:
                        results.append(metadata)

            # Build response
            response = {
                "success": True,
                "provider": "wikimedia",
                "query": query,
                "results": results,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "has_next": len(results) == page_size,
                },
                "timestamp": helpers.get_timestamp(),
                "cached": False,
            }

            # Cache result
            await cache_service.set(cache_key, response)

            return response

        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            raise
