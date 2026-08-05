from app.utils.time import utcnow

from sqlmodel import Session, select, func
from ..models.user import Generation, User, Subscription
from ..models.token import AIGenerationHistory
from datetime import datetime, timedelta


class AnalyticsService:
    @staticmethod
    def get_global_usage_stats(session: Session, days: int = 30):
        """Get aggregate usage stats for the entire platform."""
        since = utcnow() - timedelta(days=days)

        # 1. Total Generations by type
        gen_stats = session.exec(
            select(Generation.type, func.count(Generation.id))
            .where(Generation.created_at >= since)
            .group_by(Generation.type)
        ).all()

        # 2. Revenue estimate (based on token costs)
        cost_stats = session.exec(
            select(func.sum(AIGenerationHistory.cost)).where(
                AIGenerationHistory.created_at >= since
            )
        ).one()

        # 3. New User Growth
        user_stats = session.exec(select(func.count(User.id)).where(User.created_at >= since)).one()

        return {
            "total_generations_by_type": {g[0]: g[1] for g in gen_stats},
            "credits_consumed": cost_stats or 0,
            "new_users": user_stats,
            "period_days": days,
        }

    @staticmethod
    def get_user_usage_stats(session: Session, user_id: int, days: int = 30):
        """Get usage stats for a specific user."""
        since = utcnow() - timedelta(days=days)

        stats = session.exec(
            select(Generation.type, func.count(Generation.id))
            .where(Generation.user_id == user_id, Generation.created_at >= since)
            .group_by(Generation.type)
        ).all()

        return {"usage": {s[0]: s[1] for s in stats}, "period_days": days}