from app.utils.time import utcnow

from sqlmodel import Session, select
from datetime import datetime
from typing import Dict, Any
from ..models.token import APIUsage
from ..config.api_limits import ULTRA_DAILY_LIMITS, TOOL_TYPE_TO_LIMIT_KEY


class UsageTrackingService:
    @staticmethod
    def get_daily_usage(session: Session, user_id: int, tool_type: str) -> APIUsage:
        """Get or create the daily usage record for a tool."""
        today = utcnow().strftime("%Y-%m-%d")

        usage = session.exec(
            select(APIUsage).where(
                APIUsage.user_id == user_id,
                APIUsage.tool_type == tool_type,
                APIUsage.date == today,
            )
        ).first()

        if not usage:
            usage = APIUsage(user_id=user_id, tool_type=tool_type, date=today, count=0)
            session.add(usage)
            session.commit()
            session.refresh(usage)

        return usage

    @staticmethod
    def check_limit(session: Session, user_id: int, tool_type: str, plan: str) -> bool:
        """Check if the user has reached their daily limit for a tool."""
        # Check if user is admin
        from ..models.user import User

        user = session.get(User, user_id)
        if user and user.role == "ADMIN":
            return True  # Admin bypass

        if plan.upper() != "ULTRA":
            # For non-ultra users, we might use a different logic (credits)
            # but for this specific API request, we assume it's Ultra-focused
            return True

        limit_key = TOOL_TYPE_TO_LIMIT_KEY.get(tool_type.lower())
        if not limit_key:
            return True  # No limit defined

        max_limit = ULTRA_DAILY_LIMITS.get(limit_key, 0)
        usage = UsageTrackingService.get_daily_usage(session, user_id, tool_type)

        return usage.count < max_limit

    @staticmethod
    def increment_usage(session: Session, user_id: int, tool_type: str):
        """Increment the usage count for a tool."""
        usage = UsageTrackingService.get_daily_usage(session, user_id, tool_type)
        usage.count += 1
        usage.last_requested_at = utcnow()
        session.add(usage)
        session.commit()

    @staticmethod
    def get_usage_summary(session: Session, user_id: int) -> Dict[str, Any]:
        """Get a summary of daily usage vs limits for a user."""
        today = utcnow().strftime("%Y-%m-%d")
        usages = session.exec(
            select(APIUsage).where(APIUsage.user_id == user_id, APIUsage.date == today)
        ).all()

        summary = {}
        for usage in usages:
            limit_key = TOOL_TYPE_TO_LIMIT_KEY.get(usage.tool_type.lower())
            max_limit = ULTRA_DAILY_LIMITS.get(limit_key, 0)
            summary[usage.tool_type] = {
                "used": usage.count,
                "limit": max_limit,
                "remaining": max_limit - usage.count,
            }

        return summary