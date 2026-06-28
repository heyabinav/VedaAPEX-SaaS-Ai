"""
Request/Response logging middleware.
"""

import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Log request and response.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response
        """
        # Request info
        request_id = request.headers.get("X-Request-ID", "unknown")
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # Log request
        logger.info(f"[{request_id}] {method} {path} - Client: {client_ip}")

        # Start timer
        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            logger.info(
                f"[{request_id}] {method} {path} - Status: {response.status_code} - "
                f"Time: {process_time:.3f}s"
            )

            # Add response headers
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] {method} {path} - Error: {str(e)} - Time: {process_time:.3f}s",
                exc_info=True,
            )
            raise


class StructuredLoggingFormatter(logging.Formatter):
    """Structured logging formatter."""

    def format(self, record):
        """Format log record as JSON-like structure."""
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return str(log_obj)
