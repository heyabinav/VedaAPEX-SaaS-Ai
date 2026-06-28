"""
Health check routes.
"""

import logging
import time
from fastapi import APIRouter, Request
from datetime import datetime

from config import config
from schemas.responses import HealthResponse
from services.cache_service import cache_service
from utils.helpers import helpers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])

startup_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    name="Health Check",
)
async def health_check(request: Request = None):
    """
    Health check endpoint.

    Returns service status and uptime.

    **Example:**
    ```
    GET /api/v1/health
    ```
    """
    try:
        uptime = time.time() - startup_time

        logger.info(f"Health check from {request.client.host if request.client else 'unknown'}")

        return HealthResponse(
            status="healthy",
            version=config.APP_VERSION,
            timestamp=helpers.get_timestamp(),
            provider="operational",
        )

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return HealthResponse(
            status="degraded",
            version=config.APP_VERSION,
            timestamp=helpers.get_timestamp(),
            provider="error",
        )
