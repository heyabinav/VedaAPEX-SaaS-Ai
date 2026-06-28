"""
VedaApex Video Search Backend - Main Application
Production-ready FastAPI backend for image and video search using Pexels API
"""

import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from config import config
from middleware.logging import LoggingMiddleware, StructuredLoggingFormatter
from middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware
from routes import images, videos, health
from services.cache_service import cache_service
from utils.helpers import helpers

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================


def setup_logging():
    """Configure structured logging."""
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: {config.LOG_LEVEL}")


# ============================================================================
# FASTAPI APPLICATION SETUP
# ============================================================================


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=config.APP_NAME,
        version=config.APP_VERSION,
        description="Production-ready image and video search backend using Pexels API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    return app


# Create application instance
app = create_app()

logger = logging.getLogger(__name__)

# ============================================================================
# MIDDLEWARE SETUP
# ============================================================================

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    max_requests=config.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)

# Add logging middleware (should be last)
app.add_middleware(LoggingMiddleware)

# ============================================================================
# EVENT HANDLERS
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("=" * 80)
    logger.info(f"🚀 {config.APP_NAME} v{config.APP_VERSION}")
    logger.info("=" * 80)
    logger.info(f"Environment: {config.APP_ENV}")
    logger.info(f"Cache Type: {config.CACHE_TYPE}")
    logger.info(f"Cache Enabled: {config.CACHE_ENABLED}")
    logger.info(f"Rate Limiting: {config.RATE_LIMIT_ENABLED}")
    logger.info(f"Rate Limit: {config.RATE_LIMIT_PER_MINUTE} req/min")
    logger.info(f"API Auth: {config.ENABLE_API_KEY_AUTH}")
    logger.info("=" * 80)

    # Initialize cache service
    try:
        await cache_service.initialize()
        logger.info("✅ Cache service initialized")
    except Exception as e:
        logger.error(f"❌ Cache initialization failed: {e}")

    # Validate configuration
    try:
        config.validate_config()
        logger.info("✅ Configuration validated")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("🛑 Application shutting down...")


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")

    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": exc.errors(),
            "timestamp": helpers.get_timestamp(),
        },
    )


@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "NotFound",
            "message": "Endpoint not found",
            "path": str(request.url.path),
            "timestamp": helpers.get_timestamp(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.exception(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "timestamp": helpers.get_timestamp(),
        },
    )


# ============================================================================
# ROUTES
# ============================================================================

# Include image search routes
app.include_router(images.router)

# Include video search routes
app.include_router(videos.router)

# Include health check routes
app.include_router(health.router)


# ============================================================================
# ROOT ENDPOINT
# ============================================================================


@app.get("/", tags=["info"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "running",
        "environment": config.APP_ENV,
        "documentation": "/docs",
        "health": "/api/v1/health",
        "endpoints": {
            "images": {
                "search": "GET /api/v1/images/search",
                "suggestions": "GET /api/v1/images/suggestions",
            },
            "videos": {
                "search": "GET /api/v1/videos/search",
                "suggestions": "GET /api/v1/videos/suggestions",
            },
            "cache": {
                "stats": "GET /api/v1/cache/stats",
                "clear": "POST /api/v1/cache/clear",
            },
        },
    }


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Setup logging
    setup_logging()

    # Run application
    uvicorn.run(
        "app:app",
        host=config.HOST,
        port=config.PORT,
        reload=not config.is_production(),
        log_level=config.LOG_LEVEL.lower(),
    )
