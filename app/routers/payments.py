from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/payments", tags=["Payments"])


class CreatePaymentOrderRequest(BaseModel):
    plan_slug: str
    notes: Optional[dict[str, Any]] = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    metadata: Optional[dict[str, Any]] = None


from app.core.config import settings


@router.get("/config")
async def get_payment_config():
    """Return public Razorpay configuration for frontend checkout modal."""
    return {
        "success": True,
        "key_id": settings.RAZORPAY_KEY_ID or "",
        "currency": settings.RAZORPAY_CURRENCY or "INR",
        "min_amount_paisa": int(settings.RAZORPAY_MIN_AMOUNT_PAISA or 1000),
    }


@router.get("/history")
async def get_payment_history(
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Return payment transaction history for the authenticated user."""
    items = PaymentService.list_user_payments(session, user.id)
    return {"success": True, "data": items}


@router.post("/orders")
async def create_order(
    payload: CreatePaymentOrderRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    try:
        result = await PaymentService.create_order(session, user, payload.plan_slug, payload.notes)
        result["subscription"] = SubscriptionService.get_subscription_summary(session, user.id)
        return {"success": True, "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/verify")
async def verify_payment(
    payload: VerifyPaymentRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    try:
        result = PaymentService.verify_checkout_payment(
            session=session,
            user=user,
            razorpay_order_id=payload.razorpay_order_id,
            razorpay_payment_id=payload.razorpay_payment_id,
            razorpay_signature=payload.razorpay_signature,
            metadata=payload.metadata,
        )
        return {"success": True, "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/verify-payment")
async def verify_payment_and_upgrade(
    payload: VerifyPaymentRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    try:
        result = PaymentService.verify_checkout_payment(
            session=session,
            user=user,
            razorpay_order_id=payload.razorpay_order_id,
            razorpay_payment_id=payload.razorpay_payment_id,
            razorpay_signature=payload.razorpay_signature,
            metadata=payload.metadata,
        )
        plan_label = result.get("subscription", {}).get("plan") or result.get("subscription", {}).get("plan_label") or "Subscription"
        return {"success": True, "message": f"{plan_label} activated", "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    session: Session = Depends(get_session),
):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    try:
        PaymentService.verify_webhook_signature(raw_body, signature)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from exc

    result = PaymentService.process_webhook(session, raw_body, payload)
    return {"success": True, "data": result}
