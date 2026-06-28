"""
FastAPI application - VedaApex Media Backend
"""

import logging
import logging.config
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import config
from services.cache_service import cache_service
from middleware.logging import LoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware
from utils.helpers import helpers
from utils.exceptions import VedaApexException

# Routes
from routes import images, videos, health

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
os.makedirs("logs", exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": config.LOG_LEVEL,
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": config.LOG_LEVEL,
            "formatter": "detailed",
            "filename": config.LOG_FILE,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
        },
    },
    "loggers": {
        "": {
            "level": config.LOG_LEVEL,
            "handlers": ["console", "file"],
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    # Startup
    logger.info(f"{config.APP_NAME} starting up...")
    logger.info(f"Environment: {config.APP_ENV}")
    logger.info(f"Cache: {config.CACHE_TYPE}")
    logger.info(f"Rate limit: {config.RATE_LIMIT_PER_MINUTE} req/min")

    await cache_service.initialize()
    logger.info("Cache service initialized")

    yield

    # Shutdown
    logger.info(f"{config.APP_NAME} shutting down...")


# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="VedaApex Media - Wikimedia Commons Image & Video Search API",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan,
)

logger.info(f"Initializing {config.APP_NAME} v{config.APP_VERSION}")


# ============================================================================
# MIDDLEWARE STACK (Bottom-to-Top Execution)
# ============================================================================
# 1. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Security Headers
app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=lambda request, call_next: add_security_headers(call_next, request),
)

# 3. Rate Limiting
app.add_middleware(
    RateLimitMiddleware,
    max_requests=config.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)

# 4. Request/Response Logging
app.add_middleware(LoggingMiddleware)


async def add_security_headers(call_next, request: Request):
    """Add security headers."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================
@app.exception_handler(VedaApexException)
async def veda_apex_exception_handler(request: Request, exc: VedaApexException):
    """Handle VedaApex exceptions."""
    logger.warning(f"VedaApex exception: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.__class__.__name__,
            "message": exc.message,
            "status_code": exc.status_code,
            "timestamp": helpers.get_timestamp(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": "HTTPException",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": helpers.get_timestamp(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "InternalServerError",
            "message": "Internal server error",
            "status_code": 500,
            "timestamp": helpers.get_timestamp(),
        },
    )


# ============================================================================
# INCLUDE ROUTERS
# ============================================================================
app.include_router(images.router)
app.include_router(videos.router)
app.include_router(health.router)


# ============================================================================
# ROOT ENDPOINT
# ============================================================================
@app.get("/", name="Root")
async def root():
    """Root endpoint."""
    return {
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "docs": "/api/v1/docs",
        "provider": "wikimedia",
    }


# ============================================================================
# LOGGING
# ============================================================================
logger.info(f"{config.APP_NAME} initialized successfully")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
