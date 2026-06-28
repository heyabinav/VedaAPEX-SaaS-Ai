from fastapi import Depends, HTTPException
from app.models.user import User
from app.routers.auth import get_current_user_auth


async def require_pro(user: User = Depends(get_current_user_auth)) -> User:
    """FastAPI dependency to require any paid subscription plan (Pro, Max, Ultra)."""
    if not user.is_pro:
        raise HTTPException(
            status_code=403,
            detail="This premium feature requires a Pro subscription plan or higher. Please upgrade to unlock.",
        )
    return user


def require_plan(min_plan: str):
    """
    FastAPI dependency factory to require a specific level of subscription or higher.
    Levels: free (0) < pro (1) < max (2) < ultra (3)
    """
    PLAN_HIERARCHY = {"free": 0, "pro": 1, "max": 2, "ultra": 3}
    required_level = PLAN_HIERARCHY.get(min_plan.lower(), 0)

    async def guard(user: User = Depends(get_current_user_auth)) -> User:
        user_plan = (user.plan or "free").lower()
        user_level = PLAN_HIERARCHY.get(user_plan, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires a {min_plan.upper()} subscription plan or higher. Please upgrade to unlock.",
            )
        return user

    return guard
