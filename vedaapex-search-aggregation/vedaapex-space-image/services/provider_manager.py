"""
Provider Manager - Coordinates multiple providers with intelligent routing.
"""

import logging
from typing import Dict, List, Any, Optional
import asyncio
import hashlib

from config import config
from providers.nasa_provider import NASAProvider
from providers.wikimedia_provider import WikimediaProvider
from providers.pexels_provider import PexelsProvider
from utils.exceptions import ProviderError

logger = logging.getLogger(__name__)


class ProviderManager:
    """Manages multiple media search providers."""

    def __init__(self):
        """Initialize provider manager."""
        self.providers = {
            "nasa": NASAProvider(),
            "wikimedia": WikimediaProvider(),
            "pexels": PexelsProvider(),
        }

        self.enabled_providers = config.ENABLED_PROVIDERS.split(",")
        logger.info(f"Enabled providers: {self.enabled_providers}")

    def _categorize_query(self, query: str) -> str:
        """Categorize query to determine provider priority."""
        query_lower = query.lower()

        # Check space keywords
        for keyword in config.SPACE_KEYWORDS:
            if keyword in query_lower:
                logger.debug(f"Query '{query}' categorized as SPACE")
                return "space"

        # Check scientific keywords
        for keyword in config.SCIENTIFIC_KEYWORDS:
            if keyword in query_lower:
                logger.debug(f"Query '{query}' categorized as SCIENTIFIC")
                return "scientific"

        logger.debug(f"Query '{query}' categorized as GENERAL")
        return "general"

    def _get_provider_priority(self, query: str) -> List[str]:
        """Get provider priority for query."""
        category = self._categorize_query(query)

        if category == "space":
            priority = config.SPACE_QUERY_PRIORITY.split(",")
        elif category == "scientific":
            priority = config.SCIENTIFIC_QUERY_PRIORITY.split(",")
        else:
            priority = config.GENERAL_QUERY_PRIORITY.split(",")

        # Filter by enabled providers
        priority = [p for p in priority if p in self.enabled_providers]

        logger.info(f"Provider priority for '{query}' ({category}): {priority}")
        return priority

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on title hash."""
        if not config.DEDUPLICATION_ENABLED:
            return results

        seen_hashes = set()
        unique_results = []

        for result in results:
            title = result.get("title", "")
            title_hash = hashlib.md5(title.encode()).hexdigest()

            if title_hash not in seen_hashes:
                seen_hashes.add(title_hash)
                unique_results.append(result)

        logger.info(f"Deduplicated: {len(results)} → {len(unique_results)} results")
        return unique_results

    def _rank_results(
        self,
        results: List[Dict[str, Any]],
        provider_scores: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        """Rank results by provider score."""
        if not config.RANKING_ENABLED:
            return results

        # Add provider score to each result
        for result in results:
            provider = result.get("provider", "unknown")
            result["_score"] = provider_scores.get(provider, 0)

        # Sort by score (descending)
        results.sort(key=lambda x: x["_score"], reverse=True)

        # Remove score field before returning
        for result in results:
            result.pop("_score", None)

        logger.info(f"Ranked results by provider priority")
        return results

    async def search_images(
        self,
        query: str,
        page: int = 1,
        page_size: int = None,
    ) -> List[Dict[str, Any]]:
        """Search images from multiple providers."""
        logger.info(f"Multi-provider image search: {query}")

        provider_priority = self._get_provider_priority(query)
        all_results = []
        provider_scores = {}

        # Create score map (higher score = higher ranking)
        for idx, provider_name in enumerate(provider_priority):
            provider_scores[provider_name] = len(provider_priority) - idx

        # Fetch from providers in parallel
        tasks = []
        for provider_name in provider_priority:
            if provider_name not in self.providers:
                logger.warning(f"Provider not found: {provider_name}")
                continue

            provider = self.providers[provider_name]
            task = self._search_provider(
                provider,
                provider_name,
                "images",
                query,
                page,
                page_size,
            )
            tasks.append(task)

        # Gather results
        try:
            provider_results = await asyncio.gather(*tasks, return_exceptions=True)

            for results in provider_results:
                if isinstance(results, Exception):
                    logger.error(f"Provider error: {results}")
                    continue
                all_results.extend(results)

        except Exception as e:
            logger.error(f"Error gathering provider results: {e}")

        # Deduplicate and rank
        all_results = self._deduplicate_results(all_results)
        all_results = self._rank_results(all_results, provider_scores)

        # Limit results
        all_results = all_results[: config.MAX_RESULTS]

        logger.info(f"Total results: {len(all_results)}")
        return all_results

    async def search_videos(
        self,
        query: str,
        page: int = 1,
        page_size: int = None,
    ) -> List[Dict[str, Any]]:
        """Search videos from multiple providers."""
        logger.info(f"Multi-provider video search: {query}")

        provider_priority = self._get_provider_priority(query)
        all_results = []
        provider_scores = {}

        # Create score map
        for idx, provider_name in enumerate(provider_priority):
            provider_scores[provider_name] = len(provider_priority) - idx

        # Fetch from providers in parallel
        tasks = []
        for provider_name in provider_priority:
            if provider_name not in self.providers:
                logger.warning(f"Provider not found: {provider_name}")
                continue

            provider = self.providers[provider_name]
            task = self._search_provider(
                provider,
                provider_name,
                "videos",
                query,
                page,
                page_size,
            )
            tasks.append(task)

        # Gather results
        try:
            provider_results = await asyncio.gather(*tasks, return_exceptions=True)

            for results in provider_results:
                if isinstance(results, Exception):
                    logger.error(f"Provider error: {results}")
                    continue
                all_results.extend(results)

        except Exception as e:
            logger.error(f"Error gathering provider results: {e}")

        # Deduplicate and rank
        all_results = self._deduplicate_results(all_results)
        all_results = self._rank_results(all_results, provider_scores)

        # Limit results
        all_results = all_results[: config.MAX_RESULTS]

        logger.info(f"Total results: {len(all_results)}")
        return all_results

    async def _search_provider(
        self,
        provider,
        provider_name: str,
        media_type: str,
        query: str,
        page: int,
        page_size: int,
    ) -> List[Dict[str, Any]]:
        """Search single provider."""
        try:
            if media_type == "images":
                raw_response = await provider.search_images(query, page, page_size)
            else:
                raw_response = await provider.search_videos(query, page, page_size)

            # Normalize response
            results = self._normalize_response(
                provider_name,
                media_type,
                raw_response,
            )

            logger.info(f"{provider_name}: {len(results)} {media_type} results")
            return results

        except Exception as e:
            logger.error(f"Error searching {provider_name}: {e}")
            return []

    def _normalize_response(
        self,
        provider_name: str,
        media_type: str,
        raw_response: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Normalize provider response to unified format."""
        results = []

        if provider_name == "nasa":
            results = self._normalize_nasa_response(media_type, raw_response)
        elif provider_name == "wikimedia":
            results = self._normalize_wikimedia_response(media_type, raw_response)
        elif provider_name == "pexels":
            results = self._normalize_pexels_response(media_type, raw_response)

        # Add provider info to each result
        for result in results:
            result["provider"] = provider_name

        return results

    def _normalize_nasa_response(
        self,
        media_type: str,
        raw_response: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Normalize NASA API response."""
        results = []

        collection = raw_response.get("collection", {})
        items = collection.get("items", [])

        for item in items:
            data = item.get("data", [{}])[0] if item.get("data") else {}

            # Extract URLs
            links = item.get("links", [])
            thumbnail_url = ""
            for link in links:
                if link.get("rel") == "preview":
                    thumbnail_url = link.get("href", "")
                    break

            # Build normalized result
            result = {
                "title": data.get("title", "Untitled"),
                "description": data.get("description", ""),
                "media_type": media_type.rstrip("s"),  # "images" → "image"
                "source_url": item.get("href", ""),
                "thumbnail_url": thumbnail_url,
            }

            # Add media-specific URLs
            if media_type == "images":
                result["image_url"] = thumbnail_url
            else:
                result["video_url"] = item.get("href", "")

            results.append(result)

        return results

    def _normalize_wikimedia_response(
        self,
        media_type: str,
        raw_response: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Normalize Wikimedia response."""
        # Placeholder for Wikimedia integration
        return []

    def _normalize_pexels_response(
        self,
        media_type: str,
        raw_response: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Normalize Pexels response."""
        # Placeholder for Pexels integration
        return []
