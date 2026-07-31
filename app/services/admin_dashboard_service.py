"""
Admin Dashboard Service.

Provides comprehensive analytics and metrics for the admin panel:
- Total AI requests / requests today
- Generation counts by type (images, videos, audio, documents)
- AI provider usage breakdown
- Most used models
- Storage usage
- Error logs
- API usage logs
- Revenue metrics
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select, func

from app.models.user import User
from app.models.token import (
    AIGenerationHistory,
    RequestLog,
    TokenWallet,
    APIUsage,
    TokenTransaction,
)
from app.models.asset import AIAsset, AIProviderUsageLog, ErrorLog

logger = logging.getLogger("app.admin_dashboard")


class AdminDashboardService:
    """Aggregated admin dashboard analytics."""

    @staticmethod
    def get_dashboard_overview(session: Session) -> dict:
        """Get the main dashboard overview with all key metrics."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        thirty_days_ago = now - timedelta(days=30)

        total_users = session.exec(select(func.count(User.id))).one() or 0
        active_users = session.exec(
            select(func.count(User.id)).where(User.is_active == True)
        ).one() or 0
        pro_users = session.exec(
            select(func.count(User.id)).where(User.is_pro == True)
        ).one() or 0

        total_generations = session.exec(
            select(func.count(AIGenerationHistory.id))
        ).one() or 0
        generations_today = session.exec(
            select(func.count(AIGenerationHistory.id)).where(
                AIGenerationHistory.created_at >= today_start
            )
        ).one() or 0

        gen_by_type = session.exec(
            select(
                AIGenerationHistory.type,
                func.count(AIGenerationHistory.id),
            ).group_by(AIGenerationHistory.type)
        ).all()

        images_generated = sum(
            c for t, c in gen_by_type if t in ("IMAGE", "BG_REMOVAL")
        )
        videos_generated = sum(c for t, c in gen_by_type if t == "VIDEO")
        audio_generated = sum(c for t, c in gen_by_type if t == "TTS")
        documents_generated = sum(
            c for t, c in gen_by_type if t in ("PPT", "TEXT")
        )

        total_api_requests = session.exec(
            select(func.count(RequestLog.id))
        ).one() or 0
        requests_today = session.exec(
            select(func.count(RequestLog.id)).where(
                RequestLog.created_at >= today_start
            )
        ).one() or 0

        provider_stats = session.exec(
            select(
                AIProviderUsageLog.provider,
                func.count(AIProviderUsageLog.id),
            ).where(
                AIProviderUsageLog.created_at >= thirty_days_ago
            ).group_by(AIProviderUsageLog.provider)
        ).all()

        model_stats = session.exec(
            select(
                AIProviderUsageLog.model,
                func.count(AIProviderUsageLog.id),
            ).where(
                AIProviderUsageLog.created_at >= thirty_days_ago,
                AIProviderUsageLog.model.is_not(None),
            ).group_by(AIProviderUsageLog.model).order_by(
                func.count(AIProviderUsageLog.id).desc()
            ).limit(10)
        ).all()

        total_cost = session.exec(
            select(func.sum(AIProviderUsageLog.estimated_cost_usd)).where(
                AIProviderUsageLog.created_at >= thirty_days_ago
            )
        ).one() or 0

        total_credits_used = session.exec(
            select(func.sum(AIGenerationHistory.cost)).where(
                AIGenerationHistory.created_at >= thirty_days_ago
            )
        ).one() or 0

        total_errors = session.exec(
            select(func.count(ErrorLog.id)).where(
                ErrorLog.created_at >= thirty_days_ago
            )
        ).one() or 0

        errors_today = session.exec(
            select(func.count(ErrorLog.id)).where(
                ErrorLog.created_at >= today_start
            )
        ).one() or 0

        asset_count = session.exec(
            select(func.count(AIAsset.id))
        ).one() or 0
        asset_size = session.exec(
            select(func.sum(AIAsset.file_size_bytes))
        ).one() or 0

        storage_stats = AdminDashboardService._get_storage_stats()

        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "pro": pro_users,
            },
            "requests": {
                "total": total_api_requests,
                "today": requests_today,
            },
            "generations": {
                "total": total_generations,
                "today": generations_today,
                "images": images_generated,
                "videos": videos_generated,
                "audio": audio_generated,
                "documents": documents_generated,
            },
            "ai_providers": {
                "by_provider": {p: c for p, c in provider_stats},
                "by_model": [{"model": m, "count": c} for m, c in model_stats],
                "total_cost_30d_usd": round(float(total_cost or 0), 4),
            },
            "credits": {
                "total_used_30d": total_credits_used or 0,
            },
            "errors": {
                "total_30d": total_errors,
                "today": errors_today,
            },
            "storage": {
                "total_assets": asset_count,
                "total_size_bytes": asset_size or 0,
                "total_size_mb": round((asset_size or 0) / (1024 * 1024), 2),
                **storage_stats,
            },
        }

    @staticmethod
    def get_error_logs(
        session: Session,
        page: int = 1,
        limit: int = 50,
        error_code: Optional[str] = None,
        days: int = 7,
    ) -> dict:
        """Get paginated error logs."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(ErrorLog).where(ErrorLog.created_at >= since)
        if error_code:
            query = query.where(ErrorLog.error_code == error_code)

        query = query.order_by(ErrorLog.created_at.desc())

        all_errors = session.exec(query).all()
        total = len(all_errors)
        offset = (page - 1) * limit
        errors = all_errors[offset: offset + limit]

        return {
            "errors": [
                {
                    "id": e.id,
                    "request_id": e.request_id,
                    "error_code": e.error_code,
                    "error_type": e.error_type,
                    "message": e.message,
                    "endpoint": e.endpoint,
                    "method": e.method,
                    "status_code": e.status_code,
                    "created_at": e.created_at.isoformat(),
                }
                for e in errors
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": max(1, -(-total // limit)),
            },
        }

    @staticmethod
    def get_api_usage_logs(
        session: Session,
        page: int = 1,
        limit: int = 50,
        provider: Optional[str] = None,
        days: int = 30,
    ) -> dict:
        """Get paginated AI API usage logs."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(AIProviderUsageLog).where(AIProviderUsageLog.created_at >= since)
        if provider:
            query = query.where(AIProviderUsageLog.provider == provider)

        query = query.order_by(AIProviderUsageLog.created_at.desc())

        all_logs = session.exec(query).all()
        total = len(all_logs)
        offset = (page - 1) * limit
        logs = all_logs[offset: offset + limit]

        return {
            "logs": [
                {
                    "id": l.id,
                    "user_id": l.user_id,
                    "provider": l.provider,
                    "model": l.model,
                    "generation_type": l.generation_type,
                    "status": l.status,
                    "total_tokens": l.total_tokens,
                    "estimated_cost_usd": l.estimated_cost_usd,
                    "duration_ms": l.duration_ms,
                    "error_message": l.error_message,
                    "created_at": l.created_at.isoformat(),
                }
                for l in logs
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": max(1, -(-total // limit)),
            },
        }

    @staticmethod
    def _get_storage_stats() -> dict:
        """Get storage usage stats."""
        try:
            from app.services.asset_storage_service import asset_storage
            return asset_storage.get_storage_stats()
        except Exception:
            return {"cloud_enabled": False, "local_files": 0, "local_size_mb": 0}
