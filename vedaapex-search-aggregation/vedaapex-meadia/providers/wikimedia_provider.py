"""
Wikimedia Commons API provider.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
import httpx

from config import config
from utils.exceptions import ProviderError
from utils.helpers import helpers

logger = logging.getLogger(__name__)


class WikimediaProvider:
    """Wikimedia Commons provider."""

    def __init__(self):
        """Initialize provider."""
        self.base_url = config.WIKIMEDIA_API_URL
        self.timeout = config.REQUEST_TIMEOUT
        self.max_retries = 3
        self.retry_delay = 1

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "User-Agent": config.WIKIMEDIA_USER_AGENT,
            "Accept": "application/json",
        }

    async def search_images(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search for images."""
        logger.info(f"Searching images: {query}")

        params = {
            "action": "query",
            "format": "json",
            "list": "allimages",
            "aisort": "timestamp",
            "aidir": "descending",
            "ailimit": limit,
            "aiprefix": query[:1] if query else "a",
            "aiprop": "url",
        }

        # Search by title instead of prefix
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"filetype:image {query}",
            "srlimit": limit,
            "sroffset": offset,
            "srnamespace": "6",  # File namespace
        }

        try:
            result = await self._make_request(params)
            return result
        except Exception as e:
            logger.error(f"Image search error: {e}")
            raise

    async def search_videos(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search for videos."""
        logger.info(f"Searching videos: {query}")

        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"filetype:video {query}",
            "srlimit": limit,
            "sroffset": offset,
            "srnamespace": "6",  # File namespace
        }

        try:
            result = await self._make_request(params)
            return result
        except Exception as e:
            logger.error(f"Video search error: {e}")
            raise

    async def get_file_info(self, titles: List[str]) -> Dict[str, Any]:
        """Get file information."""
        if not titles:
            return {}

        params = {
            "action": "query",
            "format": "json",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|thumbsize|thumburl",
            "iiurlwidth": 300,
            "iiurlheight": 300,
        }

        try:
            result = await self._make_request(params)
            return result
        except Exception as e:
            logger.error(f"Get file info error: {e}")
            raise

    async def _make_request(
        self,
        params: Dict[str, Any],
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        try:
            timeout = httpx.Timeout(self.timeout)

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    headers=self._get_headers(),
                )

                # Handle server errors with retry
                if response.status_code >= 500:
                    if retry_count < self.max_retries:
                        wait_time = self.retry_delay * (2**retry_count)
                        logger.warning(
                            f"Server error {response.status_code}. Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        return await self._make_request(params, retry_count + 1)

                    raise ProviderError(f"Server error: {response.status_code}")

                # Handle client errors
                if response.status_code >= 400:
                    error_text = response.text
                    raise ProviderError(f"Client error {response.status_code}: {error_text}")

                # Parse response
                data = response.json()
                logger.debug(f"Response: {response.status_code}")

                return data

        except asyncio.TimeoutError:
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2**retry_count)
                logger.warning(f"Timeout. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._make_request(params, retry_count + 1)

            raise ProviderError(f"Timeout after {self.max_retries} retries")

        except httpx.ConnectError as e:
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2**retry_count)
                logger.warning(f"Connection error: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._make_request(params, retry_count + 1)

            raise ProviderError(f"Connection error: {e}")

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise ProviderError(f"Unexpected error: {e}")
