"""API Router for unified media search endpoint."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from .service import MediaSearchService
from .models import MediaSearchRequest, MediaSearchResponse, MediaSearchErrorResponse

logger = logging.getLogger("app.routers.media_search")

router = APIRouter(prefix="/search", tags=["Media Search"])

# Initialize service
search_service = MediaSearchService()


@router.post("/media", response_model=MediaSearchResponse)
async def search_media(
    request: MediaSearchRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
) -> MediaSearchResponse:
    """
    Unified media search endpoint.
    
    Search for images, videos, or NASA space content with automatic intent detection.
    
    **Query Types:**
    - `auto`: Auto-detect based on query content (default)
    - `image`: Search for images (via Pexels)
    - `video`: Search for videos (via Pexels)
    - `space`: Search for NASA space/astronomy images
    
    **Examples:**
    
    ```json
    {
      "query": "human cell",
      "type": "auto",
      "limit": 10,
      "page": 1
    }
    ```
    
    ```json
    {
      "query": "mars rover",
      "type": "space",
      "limit": 15,
      "page": 1
    }
    ```
    
    **Response:**
    Returns normalized results with consistent structure across all providers.
    Each result includes: id, type, title, thumbnail/image/video URLs, source info, etc.
    
    **Errors:**
    - INVALID_QUERY: Query too short/long
    - UNSUPPORTED_SEARCH_TYPE: Invalid type parameter
    - IMAGE_PROVIDER_ERROR: Pexels API error
    - VIDEO_PROVIDER_ERROR: Pexels API error
    - NASA_PROVIDER_ERROR: NASA API error
    - SEARCH_TIMEOUT: Provider request timeout
    - SEARCH_RATE_LIMITED: API rate limit exceeded
    """
    try:
        response = await search_service.search(request)
        
        logger.info(
            f"User {user.id} media search: query='{request.query}' "
            f"type={request.type} results={len(response.results)}"
        )
        
        return response
        
    except RuntimeError as e:
        error_str = str(e)
        
        # Parse error code from error message
        if ":" in error_str:
            error_code, error_msg = error_str.split(":", 1)
            error_code = error_code.strip()
            error_msg = error_msg.strip()
        else:
            error_code = "SEARCH_ERROR"
            error_msg = error_str
        
        # Map error codes to HTTP status codes
        status_code = 400  # Default
        if error_code == "IMAGE_PROVIDER_ERROR":
            status_code = 502  # Bad gateway
        elif error_code == "VIDEO_PROVIDER_ERROR":
            status_code = 502
        elif error_code == "NASA_PROVIDER_ERROR":
            status_code = 502
        elif error_code == "SEARCH_TIMEOUT":
            status_code = 504  # Gateway timeout
        elif error_code == "SEARCH_RATE_LIMITED":
            status_code = 429  # Too many requests
        
        logger.error(f"Search error for user {user.id}: {error_code} - {error_msg}")
        
        raise HTTPException(
            status_code=status_code,
            detail=error_msg or error_code
        )


@router.get("/media/demo", response_model=MediaSearchResponse)
async def demo_media_search(
    query: str = Query("human cell", min_length=2, max_length=200, description="Search query"),
    search_type: str = Query("auto", description="auto, image, video, or space"),
    limit: int = Query(10, ge=1, le=50, description="Results per page"),
    page: int = Query(1, ge=1, description="Page number"),
):
    """
    Demo endpoint for media search (no authentication required).
    
    Use this to test media search functionality without authentication.
    
    **Examples:**
    - `/search/media/demo?query=human+cell` → Images of human cells
    - `/search/media/demo?query=python+tutorial&search_type=video` → Python tutorial videos
    - `/search/media/demo?query=mars+rover&search_type=space` → NASA Mars rover images
    """
    try:
        request = MediaSearchRequest(
            query=query,
            type=search_type,  # type: ignore
            limit=limit,
            page=page
        )
        
        response = await search_service.search(request)
        logger.info(f"Demo search: query='{query}' type={search_type} results={len(response.results)}")
        return response
        
    except RuntimeError as e:
        error_str = str(e)
        if ":" in error_str:
            error_code, error_msg = error_str.split(":", 1)
        else:
            error_code = "SEARCH_ERROR"
            error_msg = error_str
        
        raise HTTPException(status_code=400, detail=error_msg or error_code)
