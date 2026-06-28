"""Provider manager for coordinating multiple providers."""

import asyncio
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ProviderManager:
    """Manage and coordinate multiple search providers."""

    def __init__(self, providers: Dict):
        """
        Initialize provider manager.

        Args:
            providers: Dict of {name: provider_instance}
        """
        self.providers = providers
        logger.info(f"Initialized with {len(providers)} providers")

    async def search(
        self,
        provider: str,
        query: str,
        media_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """
        Search single provider.

        Args:
            provider: Provider name
            query: Search query
            media_type: "image" or "video"
            page: Page number
            page_size: Results per page

        Returns: Provider response
        """
        if provider not in self.providers:
            logger.error(f"Provider not found: {provider}")
            return {"collection": {"items": []}}

        prov = self.providers[provider]

        try:
            if media_type == "video":
                result = await prov.search_videos(query, page, page_size)
            else:
                result = await prov.search_images(query, page, page_size)

            logger.info(f"{provider}: Found results for '{query}'")
            return result

        except Exception as e:
            logger.error(f"{provider} error: {e}")
            return {"collection": {"items": []}}

    async def multi_search(
        self,
        providers: List[str],
        query: str,
        media_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, List[Dict]]:
        """
        Search multiple providers concurrently.

        Args:
            providers: List of provider names
            query: Search query
            media_type: "image" or "video"
            page: Page number
            page_size: Results per page

        Returns: Dict of {provider: results}
        """
        tasks = [self.search(p, query, media_type, page, page_size) for p in providers]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for provider, response in zip(providers, responses):
            if isinstance(response, Exception):
                logger.error(f"{provider} exception: {response}")
                results[provider] = []
            else:
                items = response.get("collection", {}).get("items", [])
                results[provider] = items

        logger.info(f"Multi-search complete: {[(p, len(r)) for p, r in results.items()]}")
        return results
