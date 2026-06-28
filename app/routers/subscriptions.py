import json
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select
from datetime import datetime, timedelta

from app.db.session import get_session
from app.models.user import User
from app.models.token import SubscriptionPlan, UserSubscription
from app.routers.auth import get_current_user_auth
from app.services.subscription_service import SubscriptionService
from app.services.token_service import TokenService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# ─── Get All Plans ───────────────────────────────────────
@router.get("/plans")
async def get_plans(session: Session = Depends(get_session)):
    plans = session.exec(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active == True)
        .order_by(SubscriptionPlan.sort_order)
    ).all()

    formatted = []
    for p in plans:
        formatted.append(
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "price": p.price,
                "currency": p.currency,
                "token_allocation": p.token_allocation,
                "daily_credits": p.daily_credits,
                "features": json.loads(p.features) if p.features else [],
                "billing_cycle": p.billing_cycle,
            }
        )

    return {"success": True, "data": formatted}


# ─── Get Current Subscription ────────────────────────────
@router.get("/current")
async def get_current_subscription(
    user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)
):
    sub = session.exec(select(UserSubscription).where(UserSubscription.user_id == user.id)).first()
    return {
        "success": True,
        "data": SubscriptionService.get_subscription_summary(session, user.id),
    }


# ─── Subscribe (payment-ready) ───────────────────────────
@router.post("/subscribe")
async def subscribe(
    request: Request,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    body = await request.json()
    plan_slug = body.get("plan_slug")
    payment_id = body.get("payment_id")

    plan = session.exec(select(SubscriptionPlan).where(SubscriptionPlan.slug == plan_slug)).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    sub = SubscriptionService.activate_plan(session, user, plan, payment_id=payment_id)

    # Add token allocation
    TokenService.add_credits(
        session,
        user.id,
        plan.token_allocation,
        tx_type="PURCHASE",
        description=f"{plan.name} plan subscription: +{plan.token_allocation} credits",
        ip_address=request.client.host,
        metadata={"plan_id": plan.id, "payment_id": payment_id},
    )

    return {
        "success": True,
        "message": f"Subscribed to {plan.name} plan!",
        "data": {
            "plan": plan.name,
            "credits_added": plan.token_allocation,
            "expires_at": (sub.current_period_end.isoformat() if sub.current_period_end else None),
            "subscription": SubscriptionService.get_subscription_summary(session, user.id),
        },
    }
