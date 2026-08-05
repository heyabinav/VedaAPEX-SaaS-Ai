from utils.time import utcnow

import logging
from datetime import datetime, timedelta
from sqlmodel import Session, select, create_engine
from app.models.user import User, Subscription
from app.models.token import TokenWallet, SubscriptionPlan, UserSubscription
from app.db.session import engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("upgrade_admin")


def upgrade_user(email: str):
    with Session(engine) as session:
        # 1. Find User
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            logger.error(f"User {email} not found!")
            return

        logger.info(f"Found user: {user.email} (ID: {user.id})")

        # 2. Update User basic info
        user.role = "ADMIN"
        user.is_superuser = True
        user.plan = "ultra"
        user.is_pro = True
        # Set subscription end to 100 years from now
        user.subscription_start = utcnow()
        user.subscription_end = utcnow() + timedelta(days=36500)

        session.add(user)
        logger.info("Updated User model fields.")

        # 3. Handle SubscriptionPlan (ensure Ultra exists)
        ultra_plan = session.exec(
            select(SubscriptionPlan).where(SubscriptionPlan.slug == "ultra")
        ).first()
        if not ultra_plan:
            logger.info("Ultra plan not found in SubscriptionPlan table, creating it...")
            ultra_plan = SubscriptionPlan(
                name="Ultra",
                slug="ultra",
                price=9999.0,
                token_allocation=1000000,
                daily_credits=10000,
                features='["Unlimited API Keys", "Priority Support", "All AI Models", "Unlimited generations"]',
                is_active=True,
            )
            session.add(ultra_plan)
            session.commit()
            session.refresh(ultra_plan)

        # 4. Update UserSubscription
        user_sub = session.exec(
            select(UserSubscription).where(UserSubscription.user_id == user.id)
        ).first()
        if not user_sub:
            user_sub = UserSubscription(
                user_id=user.id,
                plan_id=ultra_plan.id,
                status="active",
                current_period_start=utcnow(),
                current_period_end=user.subscription_end,
            )
        else:
            user_sub.plan_id = ultra_plan.id
            user_sub.status = "active"
            user_sub.current_period_end = user.subscription_end

        session.add(user_sub)
        logger.info("Updated UserSubscription model.")

        # 5. Update Legacy Subscription (if app uses it)
        legacy_sub = session.exec(
            select(Subscription).where(Subscription.user_id == user.id)
        ).first()
        if not legacy_sub:
            legacy_sub = Subscription(
                user_id=user.id,
                plan="ULTRA",
                status="active",
                current_period_end=user.subscription_end,
            )
        else:
            legacy_sub.plan = "ULTRA"
            legacy_sub.status = "active"
            legacy_sub.current_period_end = user.subscription_end

        session.add(legacy_sub)
        logger.info("Updated Legacy Subscription model.")

        # 6. Update Wallet balance
        wallet = session.exec(select(TokenWallet).where(TokenWallet.user_id == user.id)).first()
        if not wallet:
            wallet = TokenWallet(user_id=user.id, balance=1000000, lifetime_earned=1000000)
        else:
            wallet.balance = 1000000
            wallet.lifetime_earned = max(wallet.lifetime_earned, 1000000)

        session.add(wallet)
        logger.info("Updated TokenWallet balance to 1,000,000.")

        session.commit()
        logger.info(f"Successfully upgraded {email} to ULTRA ADMIN status permanently.")


if __name__ == "__main__":
    upgrade_user("himanshukumar892960@gmail.com")