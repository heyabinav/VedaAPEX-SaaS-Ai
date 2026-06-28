"""
Pexels Provider (Stub for integration)
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PexelsProvider:
    """Pexels provider stub."""

    async def search_images(
        self, query: str, page: int = 1, page_size: int = None
    ) -> Dict[str, Any]:
        """Search images on Pexels."""
        logger.info(f"Pexels Image Search: {query}")
        return {"photos": []}

    async def search_videos(
        self, query: str, page: int = 1, page_size: int = None
    ) -> Dict[str, Any]:
        """Search videos on Pexels."""
        logger.info(f"Pexels Video Search: {query}")
        return {"videos": []}
