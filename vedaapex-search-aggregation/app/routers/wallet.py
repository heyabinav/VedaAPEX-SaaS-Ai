from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.services.token_service import TokenService
from app.services.daily_service import DailyRewardService
from app.services.referral_service import ReferralService

router = APIRouter(prefix="/wallet", tags=["Wallet & Credits"])


# ─── Get Balance ─────────────────────────────────────────
@router.get("/balance")
async def get_balance(
    user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)
):
    wallet = TokenService.get_balance(session, user.id)
    return {
        "success": True,
        "data": {
            "balance": wallet.balance,
            "lifetime_earned": wallet.lifetime_earned,
            "lifetime_spent": wallet.lifetime_spent,
            "updated_at": wallet.updated_at.isoformat(),
        },
    }


# ─── Get Transaction History ─────────────────────────────
@router.get("/transactions")
async def get_transactions(
    page: int = 1,
    limit: int = 20,
    type: str = None,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    result = TokenService.get_transactions(session, user.id, page, limit, type)
    return {"success": True, "data": result}


# ─── Claim Daily Reward ──────────────────────────────────
@router.post("/daily-reward")
async def claim_daily_reward(
    request: Request,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    result = DailyRewardService.claim_daily_reward(session, user.id, request.client.host)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    wallet = TokenService.get_balance(session, user.id)
    result["wallet"] = {"balance": wallet.balance}
    return result


# ─── Get Streak Info ─────────────────────────────────────
@router.get("/streak")
async def get_streak_info(
    user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)
):
    streak = DailyRewardService.get_streak_info(session, user.id)
    return {"success": True, "data": streak}


# ─── Get Referral Stats ─────────────────────────────────
@router.get("/referrals")
async def get_referral_stats(
    user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)
):
    stats = ReferralService.get_referral_stats(session, user.id)
    return {"success": True, "data": stats}
