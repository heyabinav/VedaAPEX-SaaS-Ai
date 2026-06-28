"""Health check routes."""

import logging
from fastapi import APIRouter

from config import config
from schemas.responses import HealthResponse
from utils.helpers import helpers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    name="Health Check",
)
async def health_check():
    """
    Health check endpoint.

    Returns service status and available providers.

    **Example:**
    ```
    GET /api/v1/health
    ```
    """
    try:
        providers = config.ENABLED_PROVIDERS.split(",")
        logger.info("Health check")

        return HealthResponse(
            status="healthy",
            version=config.APP_VERSION,
            timestamp=helpers.get_timestamp(),
            providers=providers,
        )

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return HealthResponse(
            status="degraded",
            version=config.APP_VERSION,
            timestamp=helpers.get_timestamp(),
            providers=[],
        )
