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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])

# Track startup time for uptime calculation
startup_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    name="Health Check",
    description="Check service health and status",
)
async def health_check(request: Request = None):
    """
    Health check endpoint.

    Returns service status, version, and uptime information.

    **Response:**
    - `status`: Service status (healthy/degraded/unhealthy)
    - `version`: API version
    - `uptime`: Uptime in seconds
    - `cache_status`: Cache system status

    **Example:**
    ```
    GET /api/v1/health
    ```
    """
    try:
        # Calculate uptime
        uptime = time.time() - startup_time

        # Get cache status
        cache_stats = await cache_service.get_stats()
        cache_status = "operational" if cache_stats.get("enabled") else "disabled"

        # Determine overall status
        status_value = "healthy"

        logger.info(f"Health check from {request.client.host if request.client else 'unknown'}")

        return HealthResponse(
            status=status_value,
            version=config.APP_VERSION,
            timestamp=datetime.utcnow().isoformat(),
            uptime=uptime,
            cache_status=cache_status,
        )

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return HealthResponse(
            status="degraded",
            version=config.APP_VERSION,
            timestamp=datetime.utcnow().isoformat(),
            uptime=time.time() - startup_time,
            cache_status="error",
        )


@router.get(
    "/cache/stats",
    response_model=dict,
    name="Cache Statistics",
    description="Get cache statistics",
)
async def get_cache_stats():
    """
    Get cache statistics.

    Returns information about the cache system.

    **Example:**
    ```
    GET /api/v1/cache/stats
    ```
    """
    try:
        stats = await cache_service.get_stats()
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Cache stats error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.post(
    "/cache/clear",
    response_model=dict,
    name="Clear Cache",
    description="Clear all cached data",
)
async def clear_cache():
    """
    Clear all cached data.

    **Example:**
    ```
    POST /api/v1/cache/clear
    ```
    """
    try:
        result = await cache_service.clear()

        return {
            "success": result,
            "message": ("Cache cleared successfully" if result else "Failed to clear cache"),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Cache clear error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
