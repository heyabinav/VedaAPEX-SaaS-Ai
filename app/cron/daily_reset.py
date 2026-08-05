"""Cron jobs for daily credit distribution, session cleanup, subscription expiry."""

from utils.time import utcnow

import threading
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.db.session import engine
from app.models.user import User
from app.models.token import (
    TokenWallet,
    UserSubscription,
    UserSession,
    SubscriptionPlan,
)
from app.services.token_service import TokenService
from app.config.costs import DAILY_FREE_CREDITS


def distribute_daily_credits():
    """Give free daily credits to all active users based on their plan."""
    print("[Cron] Running daily credit distribution...")
    with Session(engine) as session:
        users = session.exec(select(User).where(User.is_active == True)).all()
        count = 0
        for user in users:
            try:
                wallet = session.exec(
                    select(TokenWallet).where(TokenWallet.user_id == user.id)
                ).first()
                if not wallet:
                    continue
                daily = DAILY_FREE_CREDITS
                sub = session.exec(
                    select(UserSubscription).where(
                        UserSubscription.user_id == user.id,
                        UserSubscription.status == "active",
                    )
                ).first()
                if sub:
                    plan = session.get(SubscriptionPlan, sub.plan_id)
                    if plan:
                        daily = plan.daily_credits or DAILY_FREE_CREDITS
                TokenService.add_credits(
                    session,
                    user.id,
                    daily,
                    tx_type="DAILY_REWARD",
                    description=f"Daily free credits: +{daily}",
                )
                count += 1
            except Exception as e:
                print(f"  Error for user {user.id}: {e}")
        print(f"[Cron] Distributed credits to {count}/{len(users)} users.")


def cleanup_expired_sessions():
    """Remove expired JWT sessions."""
    print("[Cron] Cleaning expired sessions...")
    with Session(engine) as session:
        expired = session.exec(
            select(UserSession).where(UserSession.expires_at < utcnow())
        ).all()
        for s in expired:
            session.delete(s)
        session.commit()
        print(f"[Cron] Cleaned {len(expired)} sessions.")


def expire_subscriptions():
    """Mark ended subscriptions as expired."""
    print("[Cron] Checking expired subscriptions...")
    from app.services.subscription_service import SubscriptionService

    with Session(engine) as session:
        subs = session.exec(
            select(UserSubscription).where(
                UserSubscription.status == "active",
                UserSubscription.current_period_end < utcnow(),
            )
        ).all()
        for s in subs:
            s.status = "expired"
            session.add(s)

            # Fetch user and reset convenience fields
            user = session.get(User, s.user_id)
            if user:
                SubscriptionService.deactivate_plan(session, user)
        session.commit()
        print(f"[Cron] Expired {len(subs)} subscriptions and updated user statuses.")


def reset_daily_api_usage():
    """VedaCLI: Reset all API usage counts for the new day."""
    print("[Cron] Resetting daily API usage...")
    from app.models.token import APIUsage

    with Session(engine) as session:
        today = utcnow().strftime("%Y-%m-%d")
        # We delete old records to keep DB lean, or just let new day records be created
        old_usage = session.exec(select(APIUsage).where(APIUsage.date < today)).all()
        for u in old_usage:
            session.delete(u)
        session.commit()
        print(f"[Cron] Reset {len(old_usage)} API usage records.")


def start_cron_scheduler():
    """Start background scheduler using APScheduler."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        # Run subscription expiration check immediately on startup
        try:
            expire_subscriptions()
        except Exception as e:
            print(f"[Cron Error] Failed to run initial subscription check: {e}")

        scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
        scheduler.add_job(distribute_daily_credits, "cron", hour=0, minute=0)
        scheduler.add_job(reset_daily_api_usage, "cron", hour=0, minute=5)
        scheduler.add_job(expire_subscriptions, "cron", hour=1, minute=0)
        scheduler.add_job(cleanup_expired_sessions, "cron", hour=2, minute=0)
        scheduler.start()
        print("[Cron] Cron jobs initialized (timezone: Asia/Kolkata)")
    except ImportError:
        print(
            "[Cron Warning] APScheduler not installed. Cron jobs disabled. Install with: pip install apscheduler"
        )