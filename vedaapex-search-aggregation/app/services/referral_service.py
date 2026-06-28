from sqlmodel import Session, select, func
from app.models.user import User
from app.models.token import TokenTransaction
from app.services.token_service import TokenService
from app.config.costs import REFERRAL_BONUS_CREDITS


class ReferralService:
    """Referral system with dual bonus (referrer + new user)."""

    @staticmethod
    def process_referral(
        session: Session, new_user_id: int, referral_code: str, ip_address: str = None
    ) -> dict:
        if not referral_code:
            return None

        referrer = session.exec(select(User).where(User.referral_code == referral_code)).first()

        if not referrer or referrer.id == new_user_id:
            return None

        bonus = REFERRAL_BONUS_CREDITS

        # Bonus to referrer
        TokenService.add_credits(
            session,
            referrer.id,
            bonus,
            tx_type="REFERRAL_BONUS",
            description="Referral bonus: New user signed up with your code",
            ip_address=ip_address,
            metadata={"referred_user_id": new_user_id},
        )

        # Bonus to new user
        new_user_bonus = bonus // 2
        TokenService.add_credits(
            session,
            new_user_id,
            new_user_bonus,
            tx_type="REFERRAL_BONUS",
            description="Referral welcome bonus: Signed up with referral code",
            ip_address=ip_address,
            metadata={"referrer_id": referrer.id},
        )

        return {
            "referrer_id": referrer.id,
            "referrer_bonus": bonus,
            "new_user_bonus": new_user_bonus,
        }

    @staticmethod
    def get_referral_stats(session: Session, user_id: int) -> dict:
        user = session.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        referrals = len(
            session.exec(select(User).where(User.referred_by == user.referral_code)).all()
        )

        total_earned_txs = session.exec(
            select(TokenTransaction).where(
                TokenTransaction.user_id == user_id,
                TokenTransaction.type == "REFERRAL_BONUS",
            )
        ).all()
        total_earned = sum(t.amount for t in total_earned_txs)

        return {
            "referral_code": user.referral_code,
            "total_referrals": referrals,
            "total_earned": total_earned,
        }
