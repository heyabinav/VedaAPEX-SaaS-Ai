from app.utils.time import utcnow

import hmac
import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlmodel import Session, select

from app.core.config import settings
from app.models.token import (
    PaymentOrder,
    PaymentOrderStatus,
    PaymentStatus,
    PaymentTransaction,
    SubscriptionPlan,
)
from app.models.user import User
from app.services.subscription_service import SubscriptionService
from app.services.plan_utils import display_plan_name
from app.services.token_service import TokenService


class PaymentService:
    @staticmethod
    def _ensure_configured() -> None:
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise RuntimeError("Razorpay is not configured.")

    @staticmethod
    def _build_receipt(user_id: int, plan_slug: str) -> str:
        return f"vedaapex_{user_id}_{plan_slug}_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _amount_paise(plan: SubscriptionPlan) -> int:
        amount_paise = int(round(float(plan.price) * 100))
        if amount_paise < int(settings.RAZORPAY_MIN_AMOUNT_PAISA):
            raise ValueError(
                f"Minimum payment amount is {settings.RAZORPAY_MIN_AMOUNT_PAISA} paise."
            )
        return amount_paise

    @staticmethod
    def _verify_payment_signature(order_id: str, payment_id: str, signature: str) -> None:
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid Razorpay signature.")

    @staticmethod
    async def create_order(
        session: Session,
        user: User,
        plan_slug: str,
        notes: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        PaymentService._ensure_configured()

        plan = session.exec(
            select(SubscriptionPlan).where(SubscriptionPlan.slug == plan_slug)
        ).first()
        if not plan:
            raise ValueError("Plan not found.")

        amount_paise = PaymentService._amount_paise(plan)
        receipt = PaymentService._build_receipt(user.id, plan.slug)
        currency = settings.RAZORPAY_CURRENCY or "INR"
        payload = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "notes": {
                "user_id": str(user.id),
                "plan_id": str(plan.id),
                "plan_slug": plan.slug,
                "purpose": "VEDAAPEX_SUBSCRIPTION",
                **(notes or {}),
            },
        }

        async with httpx.AsyncClient(
            timeout=30.0, auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        ) as client:
            response = await client.post("https://api.razorpay.com/v1/orders", json=payload)

        if response.status_code not in {200, 201}:
            raise RuntimeError(f"Razorpay order creation failed: {response.text}")

        order_data = response.json()
        order = PaymentOrder(
            user_id=user.id,
            plan_id=plan.id,
            provider="RAZORPAY",
            order_id=order_data["id"],
            receipt=receipt,
            amount_paise=amount_paise,
            currency=currency,
            purpose="VEDAAPEX_SUBSCRIPTION",
            status=PaymentOrderStatus.CREATED,
            notes_json=json.dumps(payload["notes"]),
            provider_payload_json=json.dumps(order_data),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(order)
        session.commit()
        session.refresh(order)

        return {
            "keyId": settings.RAZORPAY_KEY_ID,
            "order": {
                "id": order.id,
                "order_id": order.order_id,
                "amount_paise": order.amount_paise,
                "currency": order.currency,
                "receipt": order.receipt,
                "plan": plan.name,
                "plan_label": display_plan_name(plan.name or plan.slug),
                "plan_slug": plan.slug,
                "plan_price": plan.price,
                "billing_cycle": plan.billing_cycle,
                "status": order.status,
                "razorpay_order": order_data,
            },
        }

    @staticmethod
    def _finalize_payment(
        session: Session,
        user: User,
        order: PaymentOrder,
        plan: SubscriptionPlan,
        payment_id: str,
        signature: Optional[str],
        metadata: Optional[dict[str, Any]] = None,
        provider_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if signature:
            PaymentService._verify_payment_signature(order.order_id, payment_id, signature)

        if order.status == PaymentOrderStatus.PAID and order.payment_id:
            return {
                "order_id": order.order_id,
                "payment_id": order.payment_id,
                "status": "already_processed",
                "subscription": SubscriptionService.get_subscription_summary(session, user.id),
            }

        existing_transaction = session.exec(
            select(PaymentTransaction).where(PaymentTransaction.payment_order_id == order.id)
        ).first()

        if existing_transaction:
            existing_transaction.payment_id = payment_id
            existing_transaction.order_id = order.order_id
            existing_transaction.signature = signature
            existing_transaction.status = PaymentStatus.VERIFIED
            existing_transaction.amount_paise = order.amount_paise
            existing_transaction.currency = order.currency
            existing_transaction.metadata_json = (
                json.dumps(metadata) if metadata else existing_transaction.metadata_json
            )
            existing_transaction.provider_payload_json = (
                json.dumps(provider_payload)
                if provider_payload
                else existing_transaction.provider_payload_json
            )
            existing_transaction.verified_at = utcnow()
            session.add(existing_transaction)
        else:
            session.add(
                PaymentTransaction(
                    user_id=user.id,
                    payment_order_id=order.id,
                    provider="RAZORPAY",
                    payment_id=payment_id,
                    order_id=order.order_id,
                    signature=signature,
                    status=PaymentStatus.VERIFIED,
                    amount_paise=order.amount_paise,
                    currency=order.currency,
                    metadata_json=json.dumps(metadata) if metadata else None,
                    provider_payload_json=(
                        json.dumps(provider_payload) if provider_payload else None
                    ),
                    verified_at=utcnow(),
                )
            )

        order.status = PaymentOrderStatus.PAID
        order.payment_id = payment_id
        order.signature = signature
        order.paid_at = order.paid_at or utcnow()
        order.updated_at = utcnow()
        order.provider_payload_json = (
            json.dumps(provider_payload) if provider_payload else order.provider_payload_json
        )
        session.add(order)
        session.commit()

        SubscriptionService.activate_plan(session, user, plan, payment_id=payment_id)

        already_counted = metadata.get("credit_granted") if metadata else False
        if not already_counted:
            TokenService.add_credits(
                session,
                user.id,
                plan.token_allocation,
                tx_type="PURCHASE",
                description=f"{plan.name} plan subscription: +{plan.token_allocation} credits",
                metadata={
                    "plan_id": plan.id,
                    "plan_slug": plan.slug,
                    "payment_id": payment_id,
                    "order_id": order.order_id,
                },
            )

        return {
            "order_id": order.order_id,
            "payment_id": payment_id,
            "status": "verified",
            "subscription": SubscriptionService.get_subscription_summary(session, user.id),
        }

    @staticmethod
    def verify_checkout_payment(
        session: Session,
        user: User,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        order = session.exec(
            select(PaymentOrder).where(PaymentOrder.order_id == razorpay_order_id)
        ).first()
        if not order:
            raise ValueError("Payment order not found.")
        if order.user_id != user.id:
            raise ValueError("This payment order does not belong to the current user.")

        plan = session.get(SubscriptionPlan, order.plan_id)
        if not plan:
            raise ValueError("Plan not found.")

        return PaymentService._finalize_payment(
            session=session,
            user=user,
            order=order,
            plan=plan,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature,
            metadata=metadata,
        )

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, signature: Optional[str]) -> None:
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            raise RuntimeError("Razorpay webhook secret is not configured.")
        if not signature:
            raise ValueError("Missing Razorpay webhook signature.")

        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid Razorpay webhook signature.")

    @staticmethod
    def process_webhook(
        session: Session, raw_body: bytes, payload: dict[str, Any]
    ) -> dict[str, Any]:
        event = payload.get("event", "")
        entity = payload.get("payload", {})
        payment_entity = (
            (entity.get("payment") or {}).get("entity") if isinstance(entity, dict) else None
        )
        order_entity = (
            (entity.get("order") or {}).get("entity") if isinstance(entity, dict) else None
        )

        razorpay_order_id = None
        razorpay_payment_id = None

        if isinstance(payment_entity, dict):
            razorpay_order_id = payment_entity.get("order_id")
            razorpay_payment_id = payment_entity.get("id")
        if not razorpay_order_id and isinstance(order_entity, dict):
            razorpay_order_id = order_entity.get("id")

        if not razorpay_order_id:
            return {"success": True, "message": "Webhook ignored: order id not found."}

        order = session.exec(
            select(PaymentOrder).where(PaymentOrder.order_id == razorpay_order_id)
        ).first()
        if not order:
            return {
                "success": True,
                "message": "Webhook ignored: payment order not found.",
            }

        user = session.get(User, order.user_id)
        plan = session.get(SubscriptionPlan, order.plan_id)
        if not user or not plan:
            return {
                "success": True,
                "message": "Webhook ignored: user or plan not found.",
            }

        metadata = {
            "event": event,
            "webhook_processed": True,
            "credit_granted": order.status == PaymentOrderStatus.PAID,
        }

        return PaymentService._finalize_payment(
            session=session,
            user=user,
            order=order,
            plan=plan,
            payment_id=razorpay_payment_id or order.payment_id or order.order_id,
            signature=None,
            metadata=metadata,
            provider_payload=payload,
        )