"""
Pexels API provider abstraction.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import aiohttp
from config import config
from utils.exceptions import ProviderError

logger = logging.getLogger(__name__)


class PexelsProvider:
    """Pexels API provider with retry logic and timeout handling."""

    def __init__(self, api_key: str):
        """
        Initialize Pexels provider.

        Args:
            api_key: Pexels API key
        """
        self.api_key = api_key
        self.base_url = config.PEXELS_API_URL
        self.timeout = config.REQUEST_TIMEOUT
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": self.api_key,
            "Accept": "application/json",
            "User-Agent": "VedaApex-Video-Search/1.0",
        }

    async def search_images(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        sort: str = "latest",
    ) -> Dict[str, Any]:
        """
        Search for images.

        Args:
            query: Search query
            page: Page number
            per_page: Results per page
            sort: Sort order

        Returns:
            Search results

        Raises:
            ProviderError: If API request fails
        """
        endpoint = f"{self.base_url}{config.PEXELS_SEARCH_ENDPOINT}"

        params = {
            "query": query,
            "page": page,
            "per_page": per_page,
            "sort": sort,
        }

        logger.info(f"Searching images: {query} (page {page})")

        return await self._make_request("GET", endpoint, params=params)

    async def search_videos(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        sort: str = "latest",
    ) -> Dict[str, Any]:
        """
        Search for videos.

        Args:
            query: Search query
            page: Page number
            per_page: Results per page
            sort: Sort order

        Returns:
            Search results

        Raises:
            ProviderError: If API request fails
        """
        endpoint = f"{self.base_url}{config.PEXELS_VIDEOS_ENDPOINT}"

        params = {
            "query": query,
            "page": page,
            "per_page": per_page,
            "sort": sort,
        }

        logger.info(f"Searching videos: {query} (page {page})")

        return await self._make_request("GET", endpoint, params=params)

    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            json_data: JSON body
            retry_count: Current retry count

        Returns:
            Response data

        Raises:
            ProviderError: If all retries fail
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                    headers=self._get_headers(),
                ) as response:
                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", self.retry_delay))
                        if retry_count < self.max_retries:
                            logger.warning(f"Rate limited. Retrying after {retry_after}s...")
                            await asyncio.sleep(retry_after)
                            return await self._make_request(
                                method,
                                url,
                                params=params,
                                json_data=json_data,
                                retry_count=retry_count + 1,
                            )

                        raise ProviderError(f"Rate limit exceeded after {self.max_retries} retries")

                    # Handle server errors with retry
                    if response.status >= 500:
                        if retry_count < self.max_retries:
                            wait_time = self.retry_delay * (2**retry_count)
                            logger.warning(
                                f"Server error {response.status}. Retrying in {wait_time}s..."
                            )
                            await asyncio.sleep(wait_time)
                            return await self._make_request(
                                method,
                                url,
                                params=params,
                                json_data=json_data,
                                retry_count=retry_count + 1,
                            )

                        raise ProviderError(f"Server error: {response.status}")

                    # Handle client errors
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ProviderError(f"Client error {response.status}: {error_text}")

                    # Parse response
                    data = await response.json()
                    logger.debug(f"Response: {response.status}")

                    return data

        except asyncio.TimeoutError:
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2**retry_count)
                logger.warning(f"Request timeout. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._make_request(
                    method,
                    url,
                    params=params,
                    json_data=json_data,
                    retry_count=retry_count + 1,
                )

            raise ProviderError(f"Request timeout after {self.max_retries} retries")

        except aiohttp.ClientError as e:
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2**retry_count)
                logger.warning(f"Connection error: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._make_request(
                    method,
                    url,
                    params=params,
                    json_data=json_data,
                    retry_count=retry_count + 1,
                )

            raise ProviderError(f"Connection error: {e}")

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise ProviderError(f"Unexpected error: {e}")
