"""
Centralized error handlers for FastAPI.

Registers handlers for:
- AppException (custom hierarchy)
- RequestValidationError (Pydantic)
- JSONDecodeError
- HTTPException
- Generic Exception (catch-all)

Every response includes: success, error_code, message, timestamp, request_id
"""

import logging
import traceback
from datetime import datetime, timezone
from json import JSONDecodeError

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import AppException
from app.core.logging_config import SensitiveDataFilter

logger = logging.getLogger("app.error_handlers")


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    request: Request | None = None,
    details: dict | None = None,
) -> JSONResponse:
    """Build a consistent error JSON response."""
    request_id = ""
    if request:
        request_id = getattr(request.state, "request_id", "")

    body = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
    }
    if details:
        body["details"] = details

    return JSONResponse(status_code=status_code, content=body)


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            "AppException [%s] on %s %s: %s",
            exc.error_code,
            request.method,
            request.url.path,
            exc.message,
        )
        body = exc.to_dict()
        body["request_id"] = getattr(request.state, "request_id", exc.request_id)
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        readable = []
        for err in errors:
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "")
            readable.append({"field": loc, "message": msg})

        logger.warning(
            "Validation error on %s %s: %s",
            request.method,
            request.url.path,
            readable,
        )

        return _error_response(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message="Invalid request data.",
            request=request,
            details={"errors": readable, "hints": "Check field names and types."},
        )

    @app.exception_handler(JSONDecodeError)
    async def json_decode_handler(request: Request, exc: JSONDecodeError):
        logger.warning(
            "JSON decode error on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
        )
        return _error_response(
            status_code=400,
            error_code="INVALID_JSON",
            message="Malformed JSON body.",
            request=request,
            details={"hints": "Ensure request body is valid JSON."},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            "HTTPException %d on %s %s: %s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.detail,
        )

        detail = exc.detail
        if isinstance(detail, dict) and detail.get("error_code"):
            body = dict(detail)
            body.setdefault("success", False)
            body.setdefault("status_code", exc.status_code)
            body.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            body.setdefault("request_id", getattr(request.state, "request_id", ""))
            return JSONResponse(status_code=exc.status_code, content=body)

        error_code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            408: "TIMEOUT",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE",
            504: "GATEWAY_TIMEOUT",
        }

        message = detail if isinstance(detail, str) else str(detail)

        return _error_response(
            status_code=exc.status_code,
            error_code=error_code_map.get(exc.status_code, "HTTP_ERROR"),
            message=message,
            request=request,
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_handler(request: Request, exc: PydanticValidationError):
        errors = []
        for err in exc.errors():
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            errors.append({"field": loc, "message": err.get("msg", "")})

        logger.warning("Pydantic validation error on %s %s", request.method, request.url.path)

        return _error_response(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message="Request validation failed.",
            request=request,
            details={"errors": errors},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception on %s %s - %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
            str(exc),
        )

        from app.core.config import settings
        is_prod = settings.APP_ENV == "production"

        return _error_response(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred." if is_prod else str(exc),
            request=request,
            details={"error_type": type(exc).__name__} if not is_prod else None,
        )
