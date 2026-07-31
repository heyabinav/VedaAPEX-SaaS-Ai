"""
Enhanced Admin Dashboard Router.

Comprehensive admin panel endpoints for monitoring and managing the platform.

Endpoints:
- GET /api/v1/admin/dashboard - Full dashboard overview
- GET /api/v1/admin/dashboard/requests - Request metrics
- GET /api/v1/admin/dashboard/generations - Generation metrics by type
- GET /api/v1/admin/dashboard/providers - AI provider usage
- GET /api/v1/admin/dashboard/models - Most used models
- GET /api/v1/admin/dashboard/errors - Error logs
- GET /api/v1/admin/dashboard/usage-logs - API usage logs
- GET /api/v1/admin/dashboard/storage - Storage metrics
- GET /api/v1/admin/dashboard/health - System health check
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func

from app.core.exceptions import AuthorizationError
from app.db.session import get_session
from app.middleware.auth_middleware import authenticate_admin
from app.models.user import User
from app.models.token import RequestLog, AIGenerationHistory, TokenWallet, UserSubscription, SubscriptionPlan
from app.models.asset import AIAsset, AIProviderUsageLog, ErrorLog
from app.services.admin_dashboard_service import AdminDashboardService
from app.services.ai_usage_logger import AIUsageLogger

logger = logging.getLogger("app.routers.admin_dashboard")

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])


@router.get("")
async def get_dashboard_overview(
    admin: User = Depends(authenticate_admin),
    session: Session = Depends(get_session),
):
    """Full admin dashboard overview with all key metrics."""
    data = AdminDashboardService.get_dashboard_overview(session)
    return {"success": True, "data": data}


@router.get("/requests")
async def get_request_metrics(
    days: int = Query(30, ge=1, le=365),
    admin: User = Depends(authenticate_admin),
    session: Session = Depends(get_session),
):
    """Request metrics over time."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total = session.exec(
        select(func.count(RequestLog.id)).where(RequestLog.created_at >= since)
    ).one() or 0

    by_status = session.exec(
        select(
            RequestLog.status_code,
            func.count(RequestLog.id),
        ).where(RequestLog.created_at >= since).group_by(RequestLog.status_code)
    ).all()

    by_method = session.exec(
        select(
            RequestLog.method,
            func.count(RequestLog.id),
        ).where(RequestLog.created_at >= since).group_by(RequestLog.method)
    ).all()

    top_endpoints = session.exec(
        select(
            RequestLog.endpoint,
            func.count(RequestLog.id),
        ).where(RequestLog.created_at >= since)
        .group_by(RequestLog.endpoint)
        .order_by(func.count(RequestLog.id).desc())
        .limit(20)
    ).all()

    avg_response = session.exec(
        select(func.avg(RequestLog.response_time_ms)).where(
            RequestLog.created_at >= since,
            RequestLog.response_time_ms.is_not(None),
        )
    ).one()

    return {
        "success": True,
        "data": {
            "total_requests": total,
            "by_status_code": {str(s): c for s, c in by_status},
            "by_method": {m: c for m, c in by_method},
            "top_endpoints": [{"endpoint": e, "count": c} for e, c in top_endpoints],
            "avg_response_time_ms": round(float(avg_response or 0), 1),
            "period_days": days,
        },
    }


@router.get("/generations")
async def get_generation_metrics(
    days: int = Query(30, ge=1, le=365),
    admin: User = Depends(authenticate_admin),
    session: Session = Depends(get_session),
):
    """Generation metrics broken down by type and status."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    by_type = session.exec(
        select(
            AIGenerationHistory.type,
            func.count(AIGenerationHistory.id),
        ).where(AIGenerationHistory.created_at >= since)
        .group_by(AIGenerationHistory.type)
    ).all()

    by_status = session.exec(
        select(
            AIGenerationHistory.status,
            func.count(AIGenerationHistory.id),
        ).where(AIGenerationHistory.created_at >= since)
        .group_by(AIGenerationHistory.status)
    ).all()

    by_provider = session.exec(
        select(
            AIGenerationHistory.provider,
            func.count(AIGenerationHistory.id),
        ).where(
            AIGenerationHistory.created_at >= since,
            AIGenerationHistory.provider.is_not(None),
        ).group_by(AIGenerationHistory.provider)
        .order_by(func.count(AIGenerationHistory.id).desc())
        .limit(20)
    ).all()

    total_credits = session.exec(
        select(func.sum(AIGenerationHistory.cost)).where(
            AIGenerationHistory.created_at >= since
        )
    ).one()

    daily_counts = session.exec(
        select(
            func.date(AIGenerationHistory.created_at),
            func.count(AIGenerationHistory.id),
        ).where(AIGenerationHistory.created_at >= since)
        .group_by(func.date(AIGenerationHistory.created_at))
        .order_by(func.date(AIGenerationHistory.created_at))
    ).all()

    return {
        "success": True,
        "data": {
            "by_type": {t: c for t, c in by_type},
            "by_status": {s: c for s, c in by_status},
            "by_provider": {p: c for p, c in by_provider},
            "total_credits_consumed": total_credits or 0,
            "daily": [{"date": str(d), "count": c} for d, c in daily_counts],
            "period_days": days,
        },
    }


@router.get("/providers")
async def get_provider_usage(
    days: int = Query(30, ge=1, le=365),
    admin: User = Depends(authenticate_admin),
    session: Session = Depends(get_session),
):
    """Detailed AI provider usage breakdown."""
    summary = AIUsageLogger.get_usage_summary(session, days=days)
    return {"success": True, "data": summary}


@router.get("/models")
async def get_model_usage(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(authenticate_admin),
    session: Session = Depends(get_session),
):
    """Most used AI models."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    model_stats = session.exec(
        select(
            AIProviderUsageLog.model,
            AIProviderUsageLog.provider,
            func.count(AIProviderUsageLog.id),
            func.avg(AIProviderUsageLog.duration_ms),
        ).where(
            AIProviderUsageLog.created_at >= since,
            AIProviderUsageLog.model.is_not(None),
        ).group_by(AIProviderUsageLog.model, AIProviderUsageLog.provider)
        .order_by(func.count(AIProviderUsageLog.id).desc())
        .limit(limit)
    ).all()

    return {
        "success": True,
        "data": {
            "models": [
                {
                    "model": m,
                    "provider": p,
                    "count": c,
                    "avg_duration_ms": round(float(d or 0), 1),
                }
                for m, p, c, d in model_stats
            ],
            "period_days": days,
        },
    }


@router.get("/errors")
async def get_error_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    error_code: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    admin: User = Depends(authenticate_admin),
    session: Session = Depends(get_session),
):
    """Paginated error logs."""
    data = AdminDashboardService.get_error_logs(
        session, page=page, limit=limit, error_code=error_code, days=days
    )
    return {"success": True, "data": data}


@router.get("/usage-logs")
async def get_usage_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    provider: Optional[str] = None,
    days: int = Query(30, ge=1, le=90),
    admin: User = Depends(authenticate_admin),
    session: Session = Depends(get_session),
):
    """Paginated AI API usage logs."""
    data = AdminDashboardService.get_api_usage_logs(
        session, page=page, limit=limit, provider=provider, days=days
    )
    return {"success": True, "data": data}


@router.get("/storage")
async def get_storage_metrics(
    admin: User = Depends(authenticate_admin),
    session: Session = Depends(get_session),
):
    """Storage usage metrics."""
    from app.services.asset_storage_service import asset_storage

    total_assets = session.exec(
        select(func.count(AIAsset.id))
    ).one() or 0

    total_size = session.exec(
        select(func.sum(AIAsset.file_size_bytes))
    ).one() or 0

    by_type = session.exec(
        select(
            AIAsset.asset_type,
            func.count(AIAsset.id),
            func.sum(AIAsset.file_size_bytes),
        ).group_by(AIAsset.asset_type)
    ).all()

    storage_stats = asset_storage.get_storage_stats()

    return {
        "success": True,
        "data": {
            "total_assets": total_assets,
            "total_size_bytes": total_size,
            "total_size_mb": round((total_size or 0) / (1024 * 1024), 2),
            "by_type": [
                {"type": t, "count": c, "size_bytes": s or 0}
                for t, c, s in by_type
            ],
            **storage_stats,
        },
    }


@router.get("/health")
async def system_health(
    admin: User = Depends(authenticate_admin),
    session: Session = Depends(get_session),
):
    """System health check for admin monitoring."""
    checks = {}

    try:
        session.exec(select(func.count(User.id)))
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    try:
        import redis
        import os
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            r = redis.from_url(redis_url)
            r.ping()
            checks["redis"] = {"status": "healthy"}
        else:
            checks["redis"] = {"status": "not_configured"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}

    from app.services.asset_storage_service import asset_storage
    checks["storage"] = {
        "status": "healthy" if asset_storage.use_cloud else "local_only",
        "cloud_enabled": asset_storage.use_cloud,
    }

    from app.services.key_manager import key_manager
    checks["api_keys"] = {"status": "healthy", "details": key_manager.get_status()}

    overall = "healthy" if all(
        c.get("status") in ("healthy", "not_configured", "local_only")
        for c in checks.values()
    ) else "degraded"

    return {
        "success": True,
        "data": {
            "overall": overall,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
