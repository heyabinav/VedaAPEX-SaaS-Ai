import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from ..db.session import engine
from sqlmodel import Session
from ..models.token import RequestLog


class APILoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = int((time.time() - start_time) * 1000)

        # Log to DB if it's an API request
        if request.url.path.startswith("/api/v1"):
            try:
                with Session(engine) as session:
                    # Attempt to get user_id from request state if set by auth dependency
                    user_id = getattr(request.state, "user_id", None)

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
            except Exception:
                # Silently fail logging to avoid breaking the actual response
                pass

        return response
