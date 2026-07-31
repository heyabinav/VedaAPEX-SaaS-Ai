"""
Middleware to attach a unique request_id to every request and log timing.
"""

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a unique request_id to every request for tracing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id

        start_time = time.time()

        response = await call_next(request)

        duration_ms = int((time.time() - start_time) * 1000)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(duration_ms)

        return response
