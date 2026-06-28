from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.user import User
from app.models.token import (
    TokenWallet,
    AIGenerationHistory,
    TokenTransaction,
    UserSubscription,
    SubscriptionPlan,
)
from app.routers.auth import get_current_user_auth
from app.services.token_service import TokenService
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin"])


def admin_only(user: User = Depends(get_current_user_auth)) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


# ─── Get All Users ───────────────────────────────────────
@router.get("/users")
async def get_all_users(
    page: int = 1,
    limit: int = 50,
    search: str = None,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    query = select(User)
    if search:
        query = query.where((User.email.contains(search)) | (User.full_name.contains(search)))
    query = query.order_by(User.created_at.desc())

    all_users = session.exec(query).all()
    total = len(all_users)
    offset = (page - 1) * limit
    users = all_users[offset : offset + limit]

    result = []
    for u in users:
        wallet = session.exec(select(TokenWallet).where(TokenWallet.user_id == u.id)).first()
        result.append(
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "balance": wallet.balance if wallet else 0,
                "created_at": u.created_at.isoformat(),
            }
        )

    return {
        "success": True,
        "data": {
            "users": result,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": max(1, -(-total // limit)),
            },
        },
    }


# ─── Add Credits ─────────────────────────────────────────
@router.post("/credits/add")
async def add_credits(
    request: Request,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    body = await request.json()
    user_id = body.get("user_id")
    amount = body.get("amount")
    reason = body.get("reason")

    if not user_id or not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="Valid user_id and positive amount required.")

    wallet = TokenService.add_credits(
        session,
        int(user_id),
        int(amount),
        tx_type="ADMIN_CREDIT",
        description=reason or f"Admin added {amount} credits",
        ip_address=request.client.host,
        metadata={"admin_id": admin.id},
    )

    return {
        "success": True,
        "message": f"Added {amount} credits to user {user_id}",
        "data": {"balance": wallet.balance},
    }


# ─── Remove Credits ──────────────────────────────────────
@router.post("/credits/remove")
async def remove_credits(
    request: Request,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    body = await request.json()
    user_id = body.get("user_id")
    amount = body.get("amount")
    reason = body.get("reason")

    if not user_id or not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="Valid user_id and positive amount required.")

    try:
        wallet = TokenService.deduct_credits(
            session,
            int(user_id),
            int(amount),
            tx_type="ADMIN_DEBIT",
            description=reason or f"Admin removed {amount} credits",
            ip_address=request.client.host,
        )
    except ValueError as e:
        if str(e) == "INSUFFICIENT_CREDITS":
            raise HTTPException(status_code=400, detail="User has insufficient credits.")
        raise

    return {
        "success": True,
        "message": f"Removed {amount} credits from user {user_id}",
        "data": {"balance": wallet.balance},
    }


# ─── Toggle User Status ─────────────────────────────────
@router.patch("/users/{user_id}/toggle")
async def toggle_user_status(
    user_id: int,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = not user.is_active
    session.add(user)
    session.commit()

    return {
        "success": True,
        "message": f"User {'activated' if user.is_active else 'deactivated'}.",
        "data": {"is_active": user.is_active},
    }


# ─── Platform Analytics ──────────────────────────────────
@router.get("/analytics")
async def get_platform_analytics(
    days: int = 30,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    from app.services.analytics_service import AnalyticsService

    # Use the new AnalyticsService for standardized reporting
    stats = AnalyticsService.get_global_usage_stats(session, days)

    # Keep some of the legacy/quick stats
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_users_today = len(session.exec(select(User).where(User.created_at >= today_start)).all())

    stats["new_users_today"] = new_users_today

    return {"success": True, "data": stats}


# ─── API Crash / Limit Exhaustion Control ─────────────────
@router.get("/crash-status")
async def get_crash_status(admin: User = Depends(admin_only)):
    from app.services.exhaustion_service import ExhaustionService

    return {"success": True, "is_crashed": ExhaustionService.is_crashed()}


@router.post("/clear-crash")
async def clear_crash_state(admin: User = Depends(admin_only)):
    from app.services.exhaustion_service import ExhaustionService

    ExhaustionService.clear_crash()
    return {
        "success": True,
        "message": "Crash state cleared successfully. Server is back online.",
    }
