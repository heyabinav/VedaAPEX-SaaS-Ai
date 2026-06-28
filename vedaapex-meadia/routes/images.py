"""
Image search routes.
"""

import logging
from fastapi import APIRouter, Query, Request, HTTPException

from config import config
from schemas.responses import SearchResponse, ErrorResponse
from services.image_service import ImageSearchService
from providers.wikimedia_provider import WikimediaProvider
from utils.exceptions import VedaApexException, ValidationError
from utils.helpers import helpers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["images"])

provider = WikimediaProvider()
image_service = ImageSearchService(provider)


@router.get(
    "/images/search",
    response_model=SearchResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    name="Search Images",
)
async def search_images(
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    request: Request = None,
):
    """
    Search for images on Wikimedia Commons.

    **Query Parameters:**
    - `q`: Search query (required, 2-200 chars)
    - `page`: Page number (default: 1)
    - `page_size`: Results per page (default: 20, max: 100)

    **Example:**
    ```
    GET /api/v1/images/search?q=cancer%20cell&page=1&page_size=20
    ```
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"Image search: {q} from {client_ip}")

        results = await image_service.search(
            query=q,
            page=page,
            page_size=page_size,
            use_cache=config.CACHE_ENABLED,
        )

        return SearchResponse(**results)

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
