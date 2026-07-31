"""Health check routes."""

import logging
from fastapi import APIRouter
from schemas.responses import HealthResponse
from utils.helpers import helpers
from config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse, name="Health Check", operation_id="health_check")
async def health_check():
    """
    Health check endpoint.

    Returns service status and available providers.
    """
    try:
        enabled_providers = []
        if config.ENABLE_PEXELS:
            enabled_providers.append("pexels")
        if config.ENABLE_WIKIMEDIA:
            enabled_providers.append("wikimedia")
        if config.ENABLE_NASA:
            enabled_providers.append("nasa")

        logger.info("Health check")

        return HealthResponse(
            status="healthy",
            version=config.APP_VERSION,
            providers=enabled_providers,
            timestamp=helpers.get_timestamp(),
        )

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return HealthResponse(
            status="degraded",
            version=config.APP_VERSION,
            providers=[],
            timestamp=helpers.get_timestamp(),
        )
