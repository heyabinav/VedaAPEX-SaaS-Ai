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
from app.db.session import init_db
from app.email.database import init_db as init_email_db
from app.middleware.api_logger import APILoggerMiddleware

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
from app.email.routes import router as email_router

# Advanced media routes
from app.routes.media import router as media_router
from app.routes.admin import router as admin_media_router
from app.routes.processor import processor_service, router as processor_router
from app.services.key_manager import key_manager

# Configure logging
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.warning("🚀 Starting VedaCLI Backend...")
    logger.warning("Initializing SQLModel Database Tables...")
    try:
        init_db()
        logger.warning("✅ Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database tables: {e}", exc_info=True)

    logger.warning("Initializing Email Verification Database...")
    try:
        init_email_db()
        logger.warning("✅ Email verification database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize email database: {e}", exc_info=True)

    logger.warning("Starting background cron scheduler...")
    try:
        from app.cron.daily_reset import start_cron_scheduler

        start_cron_scheduler()
        logger.warning("✅ Background cron scheduler started successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to start cron scheduler: {e}", exc_info=True)

    logger.warning("Loading API key rotation manager...")
    try:
        logger.warning("✅ API Key Manager loaded")
        logger.warning("Key Status: %s", key_manager.get_status())
    except Exception as e:
        logger.warning(f"API key manager init skipped: {e}")

    logger.warning("Warming processor models...")
    try:
        await processor_service.warmup_models()
        logger.warning("✅ Processor models warmed up.")
    except Exception as e:
        logger.warning(f"Processor warmup skipped: {e}")

    yield


app = FastAPI(
    title="VedaCLI Media & Core API Hub",
    description="SaaS AI Media Processing Backend with Token-Based Billing and Queue Monitoring.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Customize validation errors to return 400 Bad Request instead of 422.
    Provides detailed error messages to help frontend developers debug.
    """
    errors = exc.errors()
    readable_errors = []
    for err in errors:
        loc = " -> ".join([str(l) for l in err.get("loc", [])])
        msg = err.get("msg")
        readable_errors.append(f"{loc}: {msg}")

    logger.warning(
        "Validation error on %s %s: %s",
        request.method,
        request.url.path,
        readable_errors,
    )

    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": "Invalid request data.",
            "detail": readable_errors,
            "hints": "Check if you are sending JSON with correct field names (email, password, fullName, referralCode).",
        },
    )


@app.exception_handler(JSONDecodeError)
async def json_decode_exception_handler(request: Request, exc: JSONDecodeError):
    """
    Handle cases where the request body is not valid JSON.
    """
    logger.warning("JSON decode error on %s %s: %s", request.method, request.url.path, str(exc))
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": "Malformed JSON body.",
            "detail": str(exc),
            "hints": "Ensure your request body is valid JSON and not empty.",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    This prevents 500 errors from leaking without logging.
    """
    logger.exception(
        "Unhandled exception on %s %s - %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        str(exc),
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error.",
            "detail": (
                str(exc) if settings.APP_ENV != "production" else "An unexpected error occurred."
            ),
            "error_type": type(exc).__name__,
        },
    )


# Add Middlewares
app.add_middleware(APILoggerMiddleware)

_allowed_origins = settings.MEDIA_ALLOWED_ORIGINS or "http://localhost:3000"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(auth_router, prefix="/api/v1")
app.include_router(ai_tools_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(generation_router, prefix="/api/v1")
app.include_router(promo_router, prefix="/api/v1")
app.include_router(subscription_router, prefix="/api/v1")
app.include_router(wallet_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(oauth_router)  # OAuth callback at /auth/callback (no prefix)
app.include_router(email_router)  # Email verification routes at /api/v1/email

# Register new advanced media routes
app.include_router(media_router, prefix="/api/v1")
app.include_router(admin_media_router, prefix="/api/v1")
app.include_router(processor_router, prefix="/api/v1")


# ────────────────────────────────────────────────────────────
# Health / Ready / Root
# ────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok"}


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
