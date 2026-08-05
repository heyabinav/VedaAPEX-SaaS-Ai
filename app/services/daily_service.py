from utils.time import utcnow

from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.models.token import DailyReward
from app.services.token_service import TokenService
from app.config.costs import get_daily_reward_credits


class DailyRewardService:
    """Daily login reward with streak tracking."""

    @staticmethod
    def claim_daily_reward(session: Session, user_id: int, ip_address: str = None) -> dict:
        today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        # Check if already claimed today
        existing = session.exec(
            select(DailyReward).where(
                DailyReward.user_id == user_id,
                DailyReward.claimed_at >= today,
                DailyReward.claimed_at < tomorrow,
            )
        ).first()

        if existing:
            return {
                "success": False,
                "message": "Daily reward already claimed today.",
                "next_claim_at": tomorrow.isoformat(),
                "streak": existing.streak,
            }

        # Calculate streak
        yesterday = today - timedelta(days=1)
        yesterday_claim = session.exec(
            select(DailyReward)
            .where(
                DailyReward.user_id == user_id,
                DailyReward.claimed_at >= yesterday,
                DailyReward.claimed_at < today,
            )
            .order_by(DailyReward.claimed_at.desc())
        ).first()

        streak = (yesterday_claim.streak + 1) if yesterday_claim else 1
        credits = get_daily_reward_credits(streak)

        # Create reward record
        reward = DailyReward(
            user_id=user_id, amount=credits, streak=streak, claimed_at=utcnow()
        )
        session.add(reward)
        session.commit()

        # Add credits to wallet
        TokenService.add_credits(
            session,
            user_id,
            credits,
            tx_type="DAILY_REWARD",
            description=f"Daily login reward (Day {streak}): +{credits} credits",
            ip_address=ip_address,
            metadata={"streak": streak, "day": streak},
        )

        return {
            "success": True,
            "credits": credits,
            "streak": streak,
            "next_claim_at": tomorrow.isoformat(),
            "message": f"Claimed {credits} credits! Streak: {streak} days",
        }

    @staticmethod
    def get_streak_info(session: Session, user_id: int) -> dict:
        today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        latest = session.exec(
            select(DailyReward)
            .where(DailyReward.user_id == user_id)
            .order_by(DailyReward.claimed_at.desc())
        ).first()

        claimed_today = False
        current_streak = 0
        if latest:
            claimed_today = today <= latest.claimed_at < tomorrow
            current_streak = latest.streak

        next_credits = get_daily_reward_credits(current_streak + 1)

        return {
            "current_streak": current_streak,
            "claimed_today": claimed_today,
            "next_reward_credits": next_credits,
            "next_claim_at": tomorrow.isoformat() if claimed_today else "now",
        }