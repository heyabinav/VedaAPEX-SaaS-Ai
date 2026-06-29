"""FastAPI Application - VedaCLI Media & Core API Hub."""

import asyncio
import json
import logging
import logging.config
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from config import config
from middleware.logging import LoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware
from utils.helpers import helpers
from utils.exceptions import VedaApexException

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover
    Client = Any
    create_client = None

# Routes
from routes import search, health

if load_dotenv:
    load_dotenv()

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
            "filename": "logs/app.log",
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
# SUPABASE CONNECTION
# ============================================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY"
)

supabase_client: Optional[Client] = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY and create_client:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Supabase client initialized successfully")
    except Exception as exc:
        logger.error("Failed to initialize Supabase client: %s", exc, exc_info=True)
        supabase_client = None
else:
    logger.warning("Supabase client not initialized: missing config or dependency")


# ============================================================================
# CHAT SCHEMAS
# ============================================================================
class ChatRequest(BaseModel):
    user_id: str
    message: str
    system_prompt: Optional[str] = None
    provider: Optional[str] = "auto"
    model: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    reply: str
    provider: Optional[str] = None
    model: Optional[str] = None
    user_details: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# SUPABASE HELPERS
# ============================================================================
def _serialize_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


async def _run_supabase_query(executor):
    return await asyncio.to_thread(executor)


async def save_user_detail(user_id: str, key: str, value: Any):
    try:
        if not supabase_client:
            return None

        payload = {"user_id": user_id, "key": key, "value": _serialize_value(value)}

        def _execute():
            return supabase_client.table("user_details").upsert(
                payload, on_conflict="user_id,key"
            ).execute()

        return await _run_supabase_query(_execute)
    except Exception as exc:
        logger.error("save_user_detail failed: %s", exc, exc_info=True)
        return None


async def get_user_details(user_id: str) -> dict[str, Any]:
    try:
        if not supabase_client:
            return {}

        def _execute():
            return (
                supabase_client.table("user_details")
                .select("key,value")
                .eq("user_id", user_id)
                .execute()
            )

        response = await _run_supabase_query(_execute)
        details: dict[str, Any] = {}
        for row in getattr(response, "data", []) or []:
            key = row.get("key")
            value = row.get("value")
            if key is not None:
                details[key] = value
        return details
    except Exception as exc:
        logger.error("get_user_details failed: %s", exc, exc_info=True)
        return {}


async def save_message(user_id: str, role: str, content: str):
    try:
        if not supabase_client:
            return None

        payload = {"user_id": user_id, "role": role, "content": content}

        def _execute():
            return supabase_client.table("chat_history").insert(payload).execute()

        return await _run_supabase_query(_execute)
    except Exception as exc:
        logger.error("save_message failed: %s", exc, exc_info=True)
        return None


async def get_history(user_id: str) -> list[dict[str, Any]]:
    try:
        if not supabase_client:
            return []

        def _execute():
            return (
                supabase_client.table("chat_history")
                .select("role,content,created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )

        response = await _run_supabase_query(_execute)
        rows = list(getattr(response, "data", []) or [])
        rows.reverse()
        return rows
    except Exception as exc:
        logger.error("get_history failed: %s", exc, exc_info=True)
        return []


# ============================================================================
# CHAT HELPERS
# ============================================================================
def _build_system_prompt(base_prompt: Optional[str], user_details: dict[str, Any]) -> str:
    system_prompt = base_prompt or "You are a helpful assistant."
    if user_details:
        detail_lines = "\n".join(f"- {key}: {value}" for key, value in user_details.items())
        system_prompt = f"{system_prompt}\n\nUser details:\n{detail_lines}"
    return system_prompt


def _normalize_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system_prompt = "You are a helpful assistant."
    chat_messages: list[dict[str, str]] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system" and content:
            system_prompt = content
        else:
            chat_messages.append({"role": role, "content": content})
    return system_prompt, chat_messages


def _extract_llm_content(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return "".join(str(item) for item in result)
    if isinstance(result, dict):
        if "choices" in result and result["choices"]:
            first_choice = result["choices"][0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content")
                    if content:
                        return str(content)
                text = first_choice.get("text")
                if text:
                    return str(text)
        if "candidates" in result and result["candidates"]:
            candidate = result["candidates"][0]
            if isinstance(candidate, dict):
                content = candidate.get("content", {})
                if isinstance(content, dict):
                    parts = content.get("parts", [])
                    if parts:
                        part = parts[0]
                        if isinstance(part, dict) and part.get("text"):
                            return str(part["text"])
    return str(result)


async def _call_chat_model(
    provider: str,
    messages: list[dict[str, str]],
    model: Optional[str] = None,
):
    provider = (provider or "auto").lower()
    system_prompt, chat_messages = _normalize_messages(messages)

    groq_key = os.environ.get("GROQ_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    selected_provider = provider
    if selected_provider == "auto":
        if groq_key:
            selected_provider = "groq"
        elif openai_key:
            selected_provider = "openai"
        elif gemini_key:
            selected_provider = "gemini"
        else:
            selected_provider = "groq"

    async with httpx.AsyncClient(timeout=120.0) as client:
        if selected_provider == "groq":
            api_key = groq_key
            if not api_key:
                raise RuntimeError("GROQ_API_KEY is not configured")
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": model or "llama3-8b-8192",
                "messages": [{"role": "system", "content": system_prompt}] + chat_messages,
                "temperature": 0.7,
            }
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json(), selected_provider, payload["model"]

        if selected_provider == "openai":
            api_key = openai_key
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            endpoint = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": model or "gpt-4o-mini",
                "messages": [{"role": "system", "content": system_prompt}] + chat_messages,
                "temperature": 0.7,
            }
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json(), selected_provider, payload["model"]

        if selected_provider == "gemini":
            api_key = gemini_key
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured")
            final_model = model or "gemini-2.0-flash"
            endpoint = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{final_model}:generateContent"
            )
            contents = []
            for item in chat_messages:
                contents.append(
                    {
                        "role": "user" if item["role"] == "user" else "model",
                        "parts": [{"text": item["content"]}],
                    }
                )
            payload = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
            }
            response = await client.post(endpoint, params={"key": api_key}, json=payload)
            response.raise_for_status()
            return response.json(), selected_provider, final_model

    raise RuntimeError(f"Unsupported provider: {selected_provider}")


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    # Startup
    logger.info(f"{config.APP_NAME} starting up...")
    logger.info(f"Version: {config.APP_VERSION}")
    logger.info(f"Environment: {config.APP_ENV}")
    logger.info(f"Cache: {config.CACHE_TYPE}")
    logger.info(f"Rate limit: {config.RATE_LIMIT_PER_MINUTE} req/min")

    yield

    # Shutdown
    logger.info(f"{config.APP_NAME} shutting down...")


# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="Unified search backend with intelligent provider routing",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan,
)

logger.info(f"Initializing {config.APP_NAME} v{config.APP_VERSION}")


# ============================================================================
# MIDDLEWARE STACK
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

# 4. Logging
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
# CHAT ENDPOINT
# ============================================================================
@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        user_details = await get_user_details(request.user_id)
        history = await get_history(request.user_id)
        await save_message(request.user_id, "user", request.message)

        system_prompt = _build_system_prompt(request.system_prompt, user_details)
        chat_messages = [{"role": "system", "content": system_prompt}] + history + [
            {"role": "user", "content": request.message}
        ]

        result, provider, model = await _call_chat_model(request.provider, chat_messages, request.model)
        reply = _extract_llm_content(result)
        await save_message(request.user_id, "assistant", reply)

        return ChatResponse(
            success=True,
            reply=reply,
            provider=provider,
            model=model,
            user_details=user_details,
            history=history,
        )
    except Exception as exc:
        logger.error("Chat endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Chat request failed")


# ============================================================================
# INCLUDE ROUTERS
# ============================================================================
app.include_router(search.router)
app.include_router(health.router)


# ============================================================================
# ROOT & UTILITY ENDPOINTS
# ============================================================================
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Favicon endpoint serving the brand logo."""
    from fastapi.responses import FileResponse
    return FileResponse("favicon.jpg", media_type="image/jpeg")


@app.get("/docs", include_in_schema=False)
async def docs_redirect():
    """Redirect root /docs to /api/v1/docs."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/docs")


@app.get("/redoc", include_in_schema=False)
async def redoc_redirect():
    """Redirect root /redoc to /api/v1/redoc."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/redoc")


@app.get("/", name="Root")
async def root():
    """Root endpoint."""
    return {
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "docs": "/api/v1/docs",
        "endpoints": {
            "search": "/api/v1/search",
            "health": "/api/v1/health",
            "chat": "/api/v1/chat",
        },
    }


logger.info(f"{config.APP_NAME} initialized successfully")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
