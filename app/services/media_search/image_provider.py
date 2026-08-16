"""Pexels Image Search Provider."""

import logging
from typing import List, Optional
import httpx

from app.core.config import settings
from .models import MediaResult, MediaSearchResponse, PaginationInfo

logger = logging.getLogger("app.services.media_search.image_provider")


class ImageSearchProvider:
    """Pexels image search provider."""
    
    BASE_URL = "https://api.pexels.com/v1"
    TIMEOUT = 10.0
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key."""
        self.api_key = api_key or settings.PEXELS_API_KEY
        if not self.api_key:
            logger.warning("PEXELS_API_KEY not configured for image search")
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        page: int = 1
    ) -> MediaSearchResponse:
        """
        Search for images using Pexels API.
        
        Args:
            query: Search query
            limit: Number of results (1-80)
            page: Page number (1-based)
            
        Returns:
            Normalized search response
        """
        if not self.api_key:
            raise RuntimeError("IMAGE_PROVIDER_ERROR: Pexels API key not configured")
        
        limit = min(max(1, limit), 80)  # Pexels max is 80
        
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params={
                        "query": query,
                        "per_page": limit,
                        "page": page,
                    },
                    headers={"Authorization": self.api_key}
                )
                
                if response.status_code == 401:
                    raise RuntimeError("IMAGE_PROVIDER_ERROR: Invalid Pexels API key")
                
                if response.status_code == 429:
                    raise RuntimeError("SEARCH_RATE_LIMITED: Pexels API rate limit exceeded")
                
                if response.status_code != 200:
                    logger.error(f"Pexels API error: {response.status_code} {response.text}")
                    raise RuntimeError(f"IMAGE_PROVIDER_ERROR: Pexels API returned {response.status_code}")
                
                data = response.json()
                
                results = []
                for item in data.get("photos", []):
                    result = MediaResult(
                        id=f"pexels_{item['id']}",
                        type="image",
                        title=item.get("alt", f"Image by {item.get('photographer', 'Unknown')}"),
                        thumbnail_url=item.get("src", {}).get("small"),
                        image_url=item.get("src", {}).get("original"),
                        source_url=item.get("url"),
                        source_name="Pexels",
                        width=item.get("width"),
                        height=item.get("height"),
                        description=item.get("alt")
                    )
                    results.append(result)
                
                pagination = PaginationInfo(
                    page=page,
                    limit=limit,
                    has_more=data.get("next_page") is not None,
                    total_available=data.get("total_results")
                )
                
                return MediaSearchResponse(
                    success=True,
                    query=query,
                    type="image",
                    provider="pexels_image",
                    results=results,
                    pagination=pagination
                )
                
        except httpx.TimeoutException:
            raise RuntimeError("SEARCH_TIMEOUT: Pexels image search timed out")
        except httpx.RequestError as e:
            logger.error(f"Pexels request error: {e}")
            raise RuntimeError(f"IMAGE_PROVIDER_ERROR: {str(e)}")
        except ValueError as e:
            logger.error(f"Pexels response parse error: {e}")
            raise RuntimeError(f"IMAGE_PROVIDER_ERROR: Failed to parse response")
