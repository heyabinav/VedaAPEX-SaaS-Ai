"""NASA Image and Video Search Provider."""

import logging
from typing import List, Optional
import httpx
from datetime import datetime

from app.core.config import settings
from .models import MediaResult, MediaSearchResponse, PaginationInfo

logger = logging.getLogger("app.services.media_search.nasa_provider")


class NASASearchProvider:
    """NASA Images and Videos API provider for space content."""
    
    BASE_URL = "https://images-api.nasa.gov/search"
    TIMEOUT = 10.0
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with NASA API key."""
        # NASA public API doesn't require key for search, but we accept it for consistency
        self.api_key = api_key or settings.NASA_API_KEY
        if self.api_key == "DEMO_KEY":
            logger.warning("NASA_API_KEY not properly configured, using public API")
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        page: int = 1
    ) -> MediaSearchResponse:
        """
        Search for space images and videos using NASA Images API.
        
        Args:
            query: Search query
            limit: Number of results (1-100)
            page: Page number (1-based)
            
        Returns:
            Normalized search response
        """
        limit = min(max(1, limit), 100)  # NASA max is 100
        
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                params = {
                    "q": query,
                    "page": page,
                    "media_type": "image,video",  # Get both images and videos
                }
                
                response = await client.get(
                    self.BASE_URL,
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"NASA API error: {response.status_code} {response.text}")
                    raise RuntimeError(f"NASA_PROVIDER_ERROR: NASA API returned {response.status_code}")
                
                data = response.json()
                results = []
                
                # Process collection items
                collection = data.get("collection", {})
                items = collection.get("items", [])
                
                # Limit results
                for item in items[:limit]:
                    try:
                        result = self._parse_item(item)
                        if result:
                            results.append(result)
                    except Exception as e:
                        logger.warning(f"Failed to parse NASA item: {e}")
                        continue
                
                pagination = PaginationInfo(
                    page=page,
                    limit=limit,
                    has_more=len(items) >= limit,
                    total_available=None
                )
                
                return MediaSearchResponse(
                    success=True,
                    query=query,
                    type="space",
                    provider="nasa",
                    results=results,
                    pagination=pagination
                )
                
        except httpx.TimeoutException:
            raise RuntimeError("SEARCH_TIMEOUT: NASA search timed out")
        except httpx.RequestError as e:
            logger.error(f"NASA request error: {e}")
            raise RuntimeError(f"NASA_PROVIDER_ERROR: {str(e)}")
        except ValueError as e:
            logger.error(f"NASA response parse error: {e}")
            raise RuntimeError(f"NASA_PROVIDER_ERROR: Failed to parse response")
    
    def _parse_item(self, item: dict) -> Optional[MediaResult]:
        """
        Parse a NASA collection item.
        
        NASA API structure:
        {
            "href": "...",  // Link to all assets
            "data": [{
                "nasa_id": "...",
                "title": "...",
                "description": "...",
                "date_created": "...",
                "media_type": "image" or "video"
            }],
            "links": [
                {
                    "href": "...",
                    "rel": "preview" or "captions"
                }
            ]
        }
        """
        try:
            data_list = item.get("data", [])
            if not data_list:
                return None
            
            data = data_list[0]
            media_type = data.get("media_type", "image")
            nasa_id = data.get("nasa_id", "unknown")
            
            title = data.get("title", "NASA Image")
            description = data.get("description", "")
            date_created = data.get("date_created", "")
            
            # Try to parse date
            try:
                date_obj = datetime.fromisoformat(date_created.replace("Z", "+00:00"))
                date_str = date_obj.strftime("%Y-%m-%d")
            except:
                date_str = date_created[:10] if date_created else None
            
            # Get media URLs from links
            links = item.get("links", [])
            image_url = None
            thumbnail_url = None
            
            for link in links:
                href = link.get("href", "")
                rel = link.get("rel", "")
                
                if rel == "preview" or "jpg" in href or "png" in href:
                    if not thumbnail_url:
                        thumbnail_url = href
                    if not image_url:
                        image_url = href
            
            # Fallback: construct URL from NASA ID if needed
            if not image_url and nasa_id != "unknown":
                # NASA Images API typically provides preview links
                pass
            
            # Source URL to NASA page
            source_url = f"https://images.nasa.gov/details/{nasa_id}" if nasa_id != "unknown" else None
            
            result = MediaResult(
                id=f"nasa_{nasa_id}",
                type="image" if media_type == "image" else "video",
                title=title,
                thumbnail_url=thumbnail_url,
                image_url=image_url if media_type == "image" else None,
                video_url=None,  # NASA doesn't provide direct video URLs easily
                source_url=source_url,
                source_name="NASA",
                width=None,
                height=None,
                description=description[:200] if description else None,
                date=date_str
            )
            
            return result
            
        except Exception as e:
            logger.warning(f"Error parsing NASA item: {e}")
            return None
