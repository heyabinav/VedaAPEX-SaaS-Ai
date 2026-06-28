"""
Video search routes.
"""

import logging
from fastapi import APIRouter, Query, Request, HTTPException, Depends, status
from datetime import datetime

from config import config
from middleware.auth import APIKeyAuth
from schemas.requests import VideoSearchRequest
from schemas.responses import VideoSearchResponse, ErrorResponse
from services.video_service import VideoSearchService
from providers.pexels_provider import PexelsProvider
from utils.exceptions import VedaApexException, ValidationError
from utils.helpers import helpers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["videos"])

# Initialize provider and service
provider = PexelsProvider(config.PEXELS_API_KEY)
video_service = VideoSearchService(provider)


@router.get(
    "/videos/search",
    response_model=VideoSearchResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    name="Search Videos",
    description="Search for videos using Pexels API",
)
async def search_videos(
    q: str = Query(..., min_length=1, max_length=256, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=80, description="Results per page"),
    sort: str = Query("latest", description="Sort order: latest, popular, trending"),
    request: Request = None,
    authenticated: bool = Depends(APIKeyAuth.verify_api_key),
):
    """
    Search for videos.

    **Query Parameters:**
    - `q`: Search query (required)
    - `page`: Page number (default: 1)
    - `page_size`: Results per page (default: 20, max: 80)
    - `sort`: Sort order (default: latest)

    **Response:**
    Returns paginated video search results with metadata.

    **Example:**
    ```
    GET /api/v1/videos/search?q=nature&page=1&page_size=20
    ```
    """
    try:
        # Log request
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"Video search: {q} from {client_ip}")

        # Search videos
        results = await video_service.search(
            query=q,
            page=page,
            page_size=page_size,
            sort=sort,
            use_cache=config.CACHE_ENABLED,
        )

        return VideoSearchResponse(**results)

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except VedaApexException as e:
        logger.error(f"Application error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.get(
    "/videos/suggestions",
    response_model=list,
    name="Get Video Search Suggestions",
    description="Get search suggestions",
)
async def get_video_suggestions(
    q: str = Query(..., min_length=1, max_length=256, description="Partial query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum suggestions"),
    authenticated: bool = Depends(APIKeyAuth.verify_api_key),
):
    """
    Get search suggestions for videos.

    **Query Parameters:**
    - `q`: Partial query string (required)
    - `limit`: Maximum suggestions (default: 10, max: 50)

    **Example:**
    ```
    GET /api/v1/videos/suggestions?q=nat&limit=10
    ```
    """
    try:
        suggestions = await video_service.get_suggestions(q, limit)
        return suggestions

    except Exception as e:
        logger.error(f"Suggestions error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get suggestions",
        )
