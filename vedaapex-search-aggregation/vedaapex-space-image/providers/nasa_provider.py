"""
NASA Image and Video Library API Provider
https://images-api.nasa.gov/
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
import httpx

from config import config
from utils.exceptions import ProviderError

logger = logging.getLogger(__name__)


class NASAProvider:
    """NASA Images and Videos provider."""

    def __init__(self):
        """Initialize NASA provider."""
        self.base_url = config.NASA_API_URL
        self.api_key = config.NASA_DEMO_KEY
        self.timeout = config.REQUEST_TIMEOUT
        self.max_retries = 3
        self.retry_delay = 1

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "User-Agent": "VedaApex-Space-Image/1.0",
            "Accept": "application/json",
        }

    def _get_params(self, query: str, media_type: str = "image", page: int = 1) -> Dict[str, str]:
        """Build NASA API request parameters."""
        items_per_page = config.DEFAULT_PAGE_SIZE
        offset = (page - 1) * items_per_page

        return {
            "q": query,
            "media_type": media_type,
            "page": str(page),
            "yearStart": "1920",  # Include historical NASA content
            "yearEnd": "2024",
            "api_key": self.api_key,
        }

    async def search_images(
        self,
        query: str,
        page: int = 1,
        page_size: int = None,
    ) -> Dict[str, Any]:
        """Search for images on NASA."""
        logger.info(f"NASA Image Search: {query} (page {page})")

        params = self._get_params(query, media_type="image", page=page)

        try:
            result = await self._make_request(params)
            return result
        except Exception as e:
            logger.error(f"NASA image search error: {e}")
            raise

    async def search_videos(
        self,
        query: str,
        page: int = 1,
        page_size: int = None,
    ) -> Dict[str, Any]:
        """Search for videos on NASA."""
        logger.info(f"NASA Video Search: {query} (page {page})")

        params = self._get_params(query, media_type="video", page=page)

        try:
            result = await self._make_request(params)
            return result
        except Exception as e:
            logger.error(f"NASA video search error: {e}")
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
                logger.debug(f"NASA request: {params.get('q')}")
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
                            f"NASA server error {response.status_code}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        return await self._make_request(params, retry_count + 1)

                    raise ProviderError(f"NASA server error: {response.status_code}")

                # Handle client errors
                if response.status_code >= 400:
                    error_text = response.text
                    logger.error(f"NASA client error {response.status_code}: {error_text}")
                    raise ProviderError(f"NASA error {response.status_code}: {error_text}")

                # Parse response
                data = response.json()
                logger.debug(f"NASA response: {response.status_code}")

                return data

        except asyncio.TimeoutError:
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2**retry_count)
                logger.warning(f"NASA timeout. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._make_request(params, retry_count + 1)

            raise ProviderError(f"NASA timeout after {self.max_retries} retries")

        except httpx.ConnectError as e:
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2**retry_count)
                logger.warning(f"NASA connection error: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._make_request(params, retry_count + 1)

            raise ProviderError(f"NASA connection error: {e}")

        except Exception as e:
            logger.error(f"NASA unexpected error: {e}", exc_info=True)
            raise ProviderError(f"NASA unexpected error: {e}")
