"""Main search routes."""

import logging
from fastapi import APIRouter, Query, Request, HTTPException

from schemas.requests import SearchRequest
from schemas.responses import UnifiedSearchResponse, ErrorResponse
from services.unified_search_service import UnifiedSearchService
from providers.provider_manager import ProviderManager
from providers.mock_providers import PexelsProvider, WikimediaProvider, NASAProvider
from services.cache_service import CacheService
from utils.exceptions import VedaApexException, ValidationError
from config import config
from utils.helpers import helpers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["search"])

# Initialize services
providers = {
    "pexels": PexelsProvider(),
    "wikimedia": WikimediaProvider(),
    "nasa": NASAProvider(),
}
pm = ProviderManager(providers)
cache = CacheService(config.CACHE_TYPE, config.REDIS_URL)
search_service = UnifiedSearchService(pm, cache)


@router.get(
    "/search",
    response_model=UnifiedSearchResponse,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
    name="Unified Search",
)
async def unified_search(
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    media_type: str = Query("image", description="image or video"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    request: Request = None,
):
    """
    Unified search endpoint with intelligent provider routing.

    Automatically selects the best provider based on query content:
    - Space queries (mars, moon, etc) → NASA
    - Scientific queries (cancer cell, etc) → Wikimedia
    - General queries → Pexels

    Falls back to secondary providers if primary has issues.

    **Example:** GET /api/v1/search?q=cancer%20cell&media_type=image
    """
    try:
        result = await search_service.search(q, media_type, page, page_size)
        return UnifiedSearchResponse(**result)

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except VedaApexException as e:
        logger.error(f"Application error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
