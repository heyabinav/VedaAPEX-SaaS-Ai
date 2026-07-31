"""
AI Provider Usage Logger.

Logs every AI provider call with:
- Provider, Model, Timestamp, User ID, IP, Endpoint
- Token usage, Cost (if available)
- Status and error details

Writes to database table and api.log file.
"""

import hashlib
import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session

from app.core.security_utils import mask_api_key

logger = logging.getLogger("app.ai_usage")


class AIUsageLogger:
    """Centralized AI provider usage tracking."""

    @staticmethod
    def log_request(
        session: Session,
        *,
        user_id: Optional[int] = None,
        request_id: Optional[str] = None,
        provider: str,
        model: Optional[str] = None,
        endpoint: Optional[str] = None,
        generation_type: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_payload: Optional[dict] = None,
        response_size_bytes: Optional[int] = None,
    ) -> None:
        """Log an AI provider API call to the database and file log."""
        try:
            from app.models.asset import AIProviderUsageLog

            payload_hash = None
            if request_payload:
                payload_str = json.dumps(request_payload, sort_keys=True, default=str)
                payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]

            log_entry = AIProviderUsageLog(
                user_id=user_id,
                request_id=request_id,
                provider=provider,
                model=model,
                endpoint=endpoint,
                generation_type=generation_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost_usd,
                status=status,
                error_message=error_message,
                status_code=status_code,
                duration_ms=duration_ms,
                ip_address=ip_address,
                user_agent=user_agent,
                request_payload_hash=payload_hash,
                response_size_bytes=response_size_bytes,
            )
            session.add(log_entry)
            session.commit()

            logger.info(
                "AI Request | Provider: %s | Model: %s | User: %s | "
                "Endpoint: %s | Tokens: %s | Cost: $%s | Status: %s | Duration: %dms",
                provider,
                model or "N/A",
                user_id or "anonymous",
                endpoint or "N/A",
                total_tokens or "N/A",
                f"{estimated_cost_usd:.4f}" if estimated_cost_usd else "N/A",
                status,
                duration_ms or 0,
            )

        except Exception as e:
            logger.error("Failed to log AI usage: %s", str(e))

    @staticmethod
    @contextmanager
    def track(
        session: Session,
        *,
        user_id: Optional[int] = None,
        request_id: Optional[str] = None,
        provider: str,
        model: Optional[str] = None,
        endpoint: Optional[str] = None,
        generation_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Context manager that automatically tracks timing and success/failure."""
        start = time.time()
        status = "success"
        error_message = None
        status_code = None

        try:
            yield
        except Exception as e:
            status = "failed"
            error_message = str(e)[:500]
            status_code = getattr(e, "status_code", 500)
            raise
        finally:
            duration_ms = int((time.time() - start) * 1000)
            AIUsageLogger.log_request(
                session,
                user_id=user_id,
                request_id=request_id,
                provider=provider,
                model=model,
                endpoint=endpoint,
                generation_type=generation_type,
                status=status,
                error_message=error_message,
                status_code=status_code,
                duration_ms=duration_ms,
                ip_address=ip_address,
                user_agent=user_agent,
            )

    @staticmethod
    def get_usage_summary(
        session: Session,
        days: int = 30,
        user_id: Optional[int] = None,
    ) -> dict:
        """Get aggregated usage summary."""
        from sqlmodel import select, func
        from app.models.asset import AIProviderUsageLog
        from datetime import timedelta

        since = datetime.now(timezone.utc) - timedelta(days=days)

        base_query = select(AIProviderUsageLog).where(AIUsageLogger._created_at_col() >= since)

        if user_id:
            base_query = base_query.where(AIProviderUsageLog.user_id == user_id)

        total = session.exec(
            select(func.count(AIProviderUsageLog.id)).where(
                AIProviderUsageLog.created_at >= since,
                *([AIProviderUsageLog.user_id == user_id] if user_id else []),
            )
        ).one()

        by_provider = session.exec(
            select(
                AIProviderUsageLog.provider,
                func.count(AIProviderUsageLog.id),
            ).where(
                AIProviderUsageLog.created_at >= since,
                *([AIProviderUsageLog.user_id == user_id] if user_id else []),
            ).group_by(AIProviderUsageLog.provider)
        ).all()

        by_status = session.exec(
            select(
                AIProviderUsageLog.status,
                func.count(AIProviderUsageLog.id),
            ).where(
                AIProviderUsageLog.created_at >= since,
                *([AIProviderUsageLog.user_id == user_id] if user_id else []),
            ).group_by(AIProviderUsageLog.status)
        ).all()

        total_tokens = session.exec(
            select(func.sum(AIProviderUsageLog.total_tokens)).where(
                AIProviderUsageLog.created_at >= since,
                *([AIProviderUsageLog.user_id == user_id] if user_id else []),
            )
        ).one()

        total_cost = session.exec(
            select(func.sum(AIProviderUsageLog.estimated_cost_usd)).where(
                AIProviderUsageLog.created_at >= since,
                *([AIProviderUsageLog.user_id == user_id] if user_id else []),
            )
        ).one()

        avg_duration = session.exec(
            select(func.avg(AIProviderUsageLog.duration_ms)).where(
                AIProviderUsageLog.created_at >= since,
                *([AIProviderUsageLog.user_id == user_id] if user_id else []),
            )
        ).one()

        return {
            "total_requests": total or 0,
            "by_provider": {p: c for p, c in by_provider},
            "by_status": {s: c for s, c in by_status},
            "total_tokens": total_tokens or 0,
            "total_cost_usd": round(float(total_cost or 0), 4),
            "avg_duration_ms": round(float(avg_duration or 0), 1),
            "period_days": days,
        }

    @staticmethod
    def _created_at_col():
        from app.models.asset import AIProviderUsageLog
        return AIProviderUsageLog.created_at
