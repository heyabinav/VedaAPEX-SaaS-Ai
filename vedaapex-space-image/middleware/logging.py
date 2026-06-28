"""
Request/Response logging middleware.
"""

import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log requests and responses."""

    async def dispatch(self, request: Request, call_next):
        """Log middleware."""
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        logger.info(f"{method} {path} - {client_ip}")

        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            logger.info(f"{method} {path} - {response.status_code} - {process_time:.3f}s")
            response.headers["X-Process-Time"] = str(process_time)

            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"{method} {path} - Error: {e} - {process_time:.3f}s", exc_info=True)
            raise
