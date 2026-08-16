"""Pexels Video Search Provider."""

import logging
from typing import List, Optional
import httpx

from app.core.config import settings
from .models import MediaResult, MediaSearchResponse, PaginationInfo

logger = logging.getLogger("app.services.media_search.video_provider")


class VideoSearchProvider:
    """Pexels video search provider."""
    
    BASE_URL = "https://api.pexels.com/videos"
    TIMEOUT = 10.0
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key."""
        self.api_key = api_key or settings.PEXELS_API_KEY
        if not self.api_key:
            logger.warning("PEXELS_API_KEY not configured for video search")
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        page: int = 1
    ) -> MediaSearchResponse:
        """
        Search for videos using Pexels Videos API.
        
        Args:
            query: Search query
            limit: Number of results (1-80)
            page: Page number (1-based)
            
        Returns:
            Normalized search response
        """
        if not self.api_key:
            raise RuntimeError("VIDEO_PROVIDER_ERROR: Pexels API key not configured")
        
        limit = min(max(1, limit), 80)  # Pexels max is 80
        per_page = limit
        
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params={
                        "query": query,
                        "per_page": per_page,
                        "page": page,
                    },
                    headers={"Authorization": self.api_key}
                )
                
                if response.status_code == 401:
                    raise RuntimeError("VIDEO_PROVIDER_ERROR: Invalid Pexels API key")
                
                if response.status_code == 429:
                    raise RuntimeError("SEARCH_RATE_LIMITED: Pexels API rate limit exceeded")
                
                if response.status_code != 200:
                    logger.error(f"Pexels Videos API error: {response.status_code} {response.text}")
                    raise RuntimeError(f"VIDEO_PROVIDER_ERROR: Pexels API returned {response.status_code}")
                
                data = response.json()
                
                results = []
                for video_item in data.get("videos", []):
                    # Get best quality video file
                    video_files = video_item.get("video_files", [])
                    video_url = None
                    if video_files:
                        # Prefer high quality
                        video_url = video_files[0].get("link")
                    
                    # Get thumbnail
                    thumbnail_url = video_item.get("image")
                    
                    # Get duration
                    duration_seconds = video_item.get("duration", 0)
                    duration = self._format_duration(duration_seconds)
                    
                    result = MediaResult(
                        id=f"pexels_video_{video_item['id']}",
                        type="video",
                        title=video_item.get("user", {}).get("name", "Pexels Video"),
                        thumbnail_url=thumbnail_url,
                        video_url=video_url,
                        source_url=video_item.get("url"),
                        source_name="Pexels",
                        duration=duration,
                        channel=video_item.get("user", {}).get("name"),
                        description=None
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
                    type="video",
                    provider="pexels_video",
                    results=results,
                    pagination=pagination
                )
                
        except httpx.TimeoutException:
            raise RuntimeError("SEARCH_TIMEOUT: Pexels video search timed out")
        except httpx.RequestError as e:
            logger.error(f"Pexels video request error: {e}")
            raise RuntimeError(f"VIDEO_PROVIDER_ERROR: {str(e)}")
        except ValueError as e:
            logger.error(f"Pexels video response parse error: {e}")
            raise RuntimeError(f"VIDEO_PROVIDER_ERROR: Failed to parse response")
    
    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Convert seconds to HH:MM:SS format."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
