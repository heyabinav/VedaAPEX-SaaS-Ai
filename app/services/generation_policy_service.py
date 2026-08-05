from utils.time import utcnow

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from ..config.costs import GENERATION_COSTS, SUBSCRIPTION_PLANS
from ..models.token import AIGenerationHistory
from ..models.user import User
from .plan_utils import is_paid_plan, normalize_plan_code
from .token_service import TokenService

TYPE_TO_COST_KEY = {
    "image": "IMAGE",
    "video": "VIDEO",
    "text": "TEXT",
    "prompt": "TEXT",
    "3d": "MODEL_3D",
    "tts": "TTS",
    "logo": "IMAGE",
    "bg_removal": "BG_REMOVAL",
    "image_enhance": "IMAGE",
    "ppt": "PPT",
    "word": "TEXT",
    "excel": "TEXT",
    "pdf": "TEXT",
    "animation": "VIDEO",
    "code": "TEXT",
    "design": "IMAGE",
    "ads": "TEXT",
    "home_design": "IMAGE",
    "interior_design": "IMAGE",
    "home_map": "IMAGE",
    "color_suggestions": "TEXT",
    "edit_3d": "MODEL_3D",
}


@dataclass
class GenerationPolicy:
    plan_name: str
    cost_key: str
    usage_cost: int
    daily_credit_limit: Optional[int]
    daily_credits_used: int
    daily_credits_remaining: Optional[int]
    wallet_balance: int
    use_daily_free_route: bool
    allow_premium_fallback: bool
    charge_wallet_on_success: bool


class GenerationPolicyService:
    @staticmethod
    def get_plan_name(user: User) -> str:
        if user.subscription and user.subscription.status == "active":
            return normalize_plan_code(user.subscription.plan)

        if (
            user.user_subscription
            and user.user_subscription.status == "active"
            and user.user_subscription.plan
        ):
            return normalize_plan_code(
                user.user_subscription.plan.slug or user.user_subscription.plan.name
            )

        return "FREE"

    @staticmethod
    def get_cost_key(gen_type: str) -> str:
        return TYPE_TO_COST_KEY.get(gen_type.lower(), "TEXT")

    @staticmethod
    def get_daily_credit_limit(plan_name: str) -> Optional[int]:
        plan_code = normalize_plan_code(plan_name)
        plan_config = SUBSCRIPTION_PLANS.get(plan_code, SUBSCRIPTION_PLANS["FREE"])
        daily_credits = int(plan_config.get("daily_credits", 0))
        return None if daily_credits >= 999999 else daily_credits

    @staticmethod
    def get_daily_credits_used(session: Session, user_id: int) -> int:
        start_of_day = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        history = session.exec(
            select(AIGenerationHistory).where(
                AIGenerationHistory.user_id == user_id,
                AIGenerationHistory.status == "SUCCESS",
                AIGenerationHistory.created_at >= start_of_day,
            )
        ).all()
        return sum(max(item.cost, 0) for item in history)

    @staticmethod
    def build_policy(session: Session, user: User, gen_type: str) -> GenerationPolicy:
        plan_name = GenerationPolicyService.get_plan_name(user)
        cost_key = GenerationPolicyService.get_cost_key(gen_type)
        usage_cost = GENERATION_COSTS.get(cost_key, 1)
        daily_credit_limit = GenerationPolicyService.get_daily_credit_limit(plan_name)
        daily_credits_used = GenerationPolicyService.get_daily_credits_used(session, user.id)

        if daily_credit_limit is None:
            daily_credits_remaining = None
            use_daily_free_route = True
        else:
            daily_credits_remaining = max(daily_credit_limit - daily_credits_used, 0)
            use_daily_free_route = daily_credits_remaining >= usage_cost

        wallet = TokenService.get_balance(session, user.id)
        allow_premium_fallback = (
            use_daily_free_route or is_paid_plan(plan_name) or wallet.balance >= usage_cost
        )
        charge_wallet_on_success = plan_name == "FREE" and not use_daily_free_route

        return GenerationPolicy(
            plan_name=plan_name,
            cost_key=cost_key,
            usage_cost=usage_cost,
            daily_credit_limit=daily_credit_limit,
            daily_credits_used=daily_credits_used,
            daily_credits_remaining=daily_credits_remaining,
            wallet_balance=wallet.balance,
            use_daily_free_route=use_daily_free_route,
            allow_premium_fallback=allow_premium_fallback,
            charge_wallet_on_success=charge_wallet_on_success,
        )