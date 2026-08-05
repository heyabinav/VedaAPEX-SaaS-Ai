from app.utils.time import utcnow

import json
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from app.models.token import SubscriptionPlan, UserSubscription
from app.models.user import Subscription, User
from .plan_utils import display_plan_name, is_paid_plan, normalize_plan_code, normalize_plan_slug


class SubscriptionService:
    @staticmethod
    def get_active_subscription(
        session: Session, user_id: int
    ) -> tuple[Optional[UserSubscription], Optional[SubscriptionPlan]]:
        sub = session.exec(
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .order_by(UserSubscription.created_at.desc())
        ).first()
        if not sub:
            return None, None

        plan = session.get(SubscriptionPlan, sub.plan_id)
        return sub, plan

    @staticmethod
    def get_subscription_summary(session: Session, user_id: int) -> dict:
        sub, plan = SubscriptionService.get_active_subscription(session, user_id)
        if not sub or not plan:
            legacy = session.exec(
                select(Subscription).where(Subscription.user_id == user_id)
            ).first()
            if legacy and legacy.plan:
                plan_slug = normalize_plan_slug(legacy.plan)
                return {
                    "plan": display_plan_name(legacy.plan),
                    "plan_name": display_plan_name(legacy.plan),
                    "plan_slug": plan_slug,
                    "plan_code": normalize_plan_code(legacy.plan),
                    "status": legacy.status,
                    "features": ["Basic features"],
                    "current_period_end": (
                        legacy.current_period_end.isoformat() if legacy.current_period_end else None
                    ),
                }

            return {
                "plan": "Free",
                "plan_name": "Free",
                "plan_slug": "free",
                "plan_code": "FREE",
                "status": "active",
                "features": [
                    "100 credits on signup",
                    "10 daily free credits",
                    "Basic features",
                ],
            }

        plan_code = normalize_plan_code(plan.slug or plan.name)
        plan_label = display_plan_name(plan.name or plan.slug)
        return {
            "plan": plan_label,
            "plan_name": plan.name,
            "plan_slug": plan.slug,
            "plan_code": plan_code,
            "status": sub.status,
            "token_allocation": plan.token_allocation,
            "daily_credits": plan.daily_credits,
            "price": plan.price,
            "currency": plan.currency,
            "billing_cycle": plan.billing_cycle,
            "features": json.loads(plan.features) if plan.features else [],
            "current_period_end": (
                sub.current_period_end.isoformat() if sub.current_period_end else None
            ),
            "payment_id": sub.payment_id,
        }

    @staticmethod
    def _period_end_for_plan(plan: SubscriptionPlan) -> datetime:
        cycle = (plan.billing_cycle or "monthly").lower()
        if "year" in cycle:
            return utcnow() + timedelta(days=365)
        return utcnow() + timedelta(days=30)

    @staticmethod
    def activate_plan(
        session: Session,
        user: User,
        plan: SubscriptionPlan,
        payment_id: Optional[str] = None,
    ) -> UserSubscription:
        period_end = SubscriptionService._period_end_for_plan(plan)
        current = session.exec(
            select(UserSubscription).where(UserSubscription.user_id == user.id)
        ).first()

        if current:
            current.plan_id = plan.id
            current.status = "active"
            current.current_period_start = utcnow()
            current.current_period_end = period_end
            if payment_id:
                current.payment_id = payment_id
            session.add(current)
            sub = current
        else:
            sub = UserSubscription(
                user_id=user.id,
                plan_id=plan.id,
                status="active",
                current_period_start=utcnow(),
                current_period_end=period_end,
                payment_id=payment_id,
            )
            session.add(sub)

        legacy = session.exec(select(Subscription).where(Subscription.user_id == user.id)).first()
        legacy_plan = normalize_plan_code(plan.slug or plan.name)
        if legacy:
            legacy.plan = legacy_plan
            legacy.status = "active"
            legacy.current_period_end = period_end
            session.add(legacy)
        else:
            session.add(
                Subscription(
                    user_id=user.id,
                    plan=legacy_plan,
                    status="active",
                    current_period_end=period_end,
                )
            )

        # Update User model convenience fields
        user.plan = normalize_plan_slug(plan.slug or plan.name)
        user.is_pro = is_paid_plan(plan.slug or plan.name)
        user.subscription_start = utcnow()
        user.subscription_end = period_end
        session.add(user)

        session.commit()
        session.refresh(sub)
        session.refresh(user)
        return sub

    @staticmethod
    def deactivate_plan(session: Session, user: User) -> None:
        user.plan = "free"
        user.is_pro = False
        user.subscription_start = None
        user.subscription_end = None
        session.add(user)

        # Deactivate user subscription status
        current = session.exec(
            select(UserSubscription).where(UserSubscription.user_id == user.id)
        ).first()
        if current:
            current.status = "expired"
            session.add(current)

        legacy = session.exec(select(Subscription).where(Subscription.user_id == user.id)).first()
        if legacy:
            legacy.plan = "FREE"
            legacy.status = "expired"
            session.add(legacy)

        session.commit()
        session.refresh(user)

    @staticmethod
    def is_paid_plan(plan_name: str) -> bool:
        return is_paid_plan(plan_name)