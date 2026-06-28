from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select
from typing import List, Any
from ..db.session import get_session
from ..models.user import User
from ..models.token import APIKey
from .auth import get_current_user_auth
from ..services.api_key_service import APIKeyService
from ..services.usage_tracking_service import UsageTrackingService
from ..services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api-keys", tags=["Developer API"])


@router.post("/generate")
async def generate_key(
    name: str = "Default Key",
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Generate a new secure API key (Ultra Plan required)."""
    if not (user.subscription and user.subscription.plan.upper() == "ULTRA"):
        raise HTTPException(
            status_code=403,
            detail="Developer API access requires an active Ultra Plan.",
        )

    return APIKeyService.create_api_key(session, user.id, name)


@router.get("/list")
async def list_keys(
    user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)
):
    """List all API keys for the current user."""
    keys = APIKeyService.list_api_keys(session, user.id)
    return {
        "success": True,
        "data": [
            {
                "id": k.id,
                "name": k.name,
                "prefix": k.prefix,
                "is_active": k.is_active,
                "created_at": k.created_at,
            }
            for k in keys
        ],
    }


@router.post("/revoke/{key_id}")
async def revoke_key(
    key_id: int,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Revoke an existing API key."""
    success = APIKeyService.revoke_api_key(session, user.id, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API Key not found.")
    return {"success": True, "message": "API key revoked successfully."}


@router.get("/usage")
async def get_api_usage(
    user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)
):
    """Get detailed daily usage stats for all tools."""
    summary = UsageTrackingService.get_usage_summary(session, user.id)
    return {"success": True, "data": summary}


@router.get("/limits")
async def get_api_limits(user: User = Depends(get_current_user_auth)):
    """Get all daily limits for the Ultra Plan."""
    from ..config.api_limits import ULTRA_DAILY_LIMITS

    return {"success": True, "data": ULTRA_DAILY_LIMITS}


@router.get("/analytics")
async def get_api_analytics(
    days: int = 30,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Get historical usage analytics for the developer dashboard."""
    return {
        "success": True,
        "data": AnalyticsService.get_user_usage_stats(session, user.id, days),
    }


@router.get("/subscription")
async def get_developer_subscription(user: User = Depends(get_current_user_auth)):
    """Get current developer subscription status."""
    if not user.subscription:
        return {"success": True, "data": {"plan": "Free", "status": "inactive"}}

    return {
        "success": True,
        "data": {
            "plan": user.subscription.plan,
            "status": user.subscription.status,
            "expires_at": user.subscription.current_period_end,
        },
    }
