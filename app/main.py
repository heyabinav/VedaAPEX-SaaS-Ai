import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from json import JSONDecodeError

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.error_handlers import register_error_handlers
from app.db.session import init_db
from app.email.database import init_db as init_email_db
from app.middleware.api_logger import APILoggerMiddleware
from app.middleware.request_context import RequestContextMiddleware

# Routers
from app.routers.auth import router as auth_router
from app.routers.ai_tools import router as ai_tools_router
from app.routers.admin import router as admin_router
from app.routers.generation import router as generation_router
from app.routers.promo import router as promo_router
from app.routers.subscriptions import router as subscription_router
from app.routers.wallet import router as wallet_router
from app.routers.api_keys import router as api_keys_router
from app.routers.payments import router as payments_router
from app.routers.oauth import router as oauth_router
from app.routers.canva_router import router as canva_router
from app.routers.figma import router as figma_router
from app.routes.canva_oauth import router as canva_oauth_router
from app.routes.figma_oauth import router as figma_oauth_router
from app.routers.google import router as google_router
from app.routes.google_mcp import router as google_mcp_router
from app.routes.design_mcp import router as design_mcp_router
from app.routers.connectors import router as connectors_router
from app.routers.connector_registry import router as connector_registry_router
from app.mcp.connector_tools import router as connector_mcp_router
from app.email.routes import router as email_router

# Advanced media routes
from app.routes.media import router as media_router
from app.routes.admin import router as admin_media_router
from app.routes.processor import processor_service, router as processor_router
from app.services.key_manager import key_manager

# New routes
from app.routers.assets import router as assets_router
from app.routers.admin_dashboard import router as admin_dashboard_router

# Configure structured logging
setup_logging(env=settings.APP_ENV)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting VedaCLI Backend...")
    logger.info("Initializing SQLModel Database Tables...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize database tables: %s", e, exc_info=True)

    logger.info("Initializing Email Verification Database...")
    try:
        init_email_db()
        logger.info("Email verification database initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize email database: %s", e, exc_info=True)

    logger.info("Starting background cron scheduler...")
    try:
        from app.cron.daily_reset import start_cron_scheduler
        start_cron_scheduler()
        logger.info("Background cron scheduler started successfully.")
    except Exception as e:
        logger.error("Failed to start cron scheduler: %s", e, exc_info=True)

    logger.info("Loading API key rotation manager...")
    try:
        logger.info("API Key Manager loaded")
        logger.info("Key Status: %s", key_manager.get_status())
    except Exception as e:
        logger.warning("API key manager init skipped: %s", e)

    logger.info("Warming processor models...")
    try:
        if settings.APP_ENV.lower() == "development":
            logger.info("Skipping processor warmup in development mode.")
        else:
            await processor_service.warmup_models()
            logger.info("Processor models warmed up.")
    except Exception as e:
        logger.warning("Processor warmup skipped: %s", e)

    yield


app = FastAPI(
    title="VedaCLI Media & Core API Hub",
    description="SaaS AI Media Processing Backend with Token-Based Billing and Queue Monitoring.",
    version="2.0.0",
    lifespan=lifespan,
)

# ────────────────────────────────────────────────────────────
# Register centralized error handlers
# ────────────────────────────────────────────────────────────
register_error_handlers(app)


# ────────────────────────────────────────────────────────────
# Add Middlewares (order matters - last added = first executed)
# ────────────────────────────────────────────────────────────
app.add_middleware(APILoggerMiddleware)
app.add_middleware(RequestContextMiddleware)

_allowed_origins = settings.MEDIA_ALLOWED_ORIGINS or "http://localhost:3000"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


# ────────────────────────────────────────────────────────────
# Static files
# ────────────────────────────────────────────────────────────
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/api/v1/media/download", StaticFiles(directory=uploads_dir), name="media_downloads")


# ────────────────────────────────────────────────────────────
# Register routers
# ────────────────────────────────────────────────────────────
# Core routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(ai_tools_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(generation_router, prefix="/api/v1")
app.include_router(promo_router, prefix="/api/v1")
app.include_router(subscription_router, prefix="/api/v1")
app.include_router(wallet_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(canva_router)
app.include_router(figma_router)
app.include_router(canva_oauth_router)
app.include_router(figma_oauth_router)
app.include_router(google_router)
app.include_router(google_mcp_router)
app.include_router(design_mcp_router)
app.include_router(connectors_router)
app.include_router(connector_registry_router)
app.include_router(connector_mcp_router)
app.include_router(oauth_router)
app.include_router(email_router)

# Advanced media routes
app.include_router(media_router, prefix="/api/v1")
app.include_router(admin_media_router, prefix="/api/v1")
app.include_router(processor_router, prefix="/api/v1")

# New routes - AI Asset storage & proxy
app.include_router(assets_router, prefix="/api/v1")

# New routes - Admin Dashboard
app.include_router(admin_dashboard_router, prefix="/api/v1")


# ────────────────────────────────────────────────────────────
# Health / Ready / Root
# ────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/ready")
async def ready():
    return {"status": "ready", "service": "vedaapex-python-media"}


@app.get("/api/v1/admin/key-status", tags=["Admin"])
async def key_status():
    return key_manager.get_status()


@app.api_route("/", methods=["GET", "HEAD"])
async def home():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)




