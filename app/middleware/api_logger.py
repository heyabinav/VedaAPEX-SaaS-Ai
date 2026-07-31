"""
Enhanced API Request Logger Middleware.

Logs every /api/v1/* request to the database with:
- User ID, endpoint, method, IP, status, response time
- Request ID propagation
- Structured logging to file
"""

import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..db.session import engine
from sqlmodel import Session
from ..models.token import RequestLog

logger = logging.getLogger("app.middleware.api_logger")


class APILoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        response = await call_next(request)

        process_time = int((time.time() - start_time) * 1000)

        if request.url.path.startswith("/api/v1"):
            try:
                with Session(engine) as session:
                    user_id = getattr(request.state, "user_id", None)
                    request_id = getattr(request.state, "request_id", "")

                    log = RequestLog(
                        user_id=user_id,
                        endpoint=request.url.path,
                        method=request.method,
                        ip_address=request.client.host if request.client else "unknown",
                        status_code=response.status_code,
                        response_time_ms=process_time,
                    )
                    session.add(log)
                    session.commit()

                    logger.info(
                        "%s %s %d %dms user=%s req=%s",
                        request.method,
                        request.url.path,
                        response.status_code,
                        process_time,
                        user_id or "-",
                        request_id or "-",
                    )
            except Exception:
                pass

        return response
