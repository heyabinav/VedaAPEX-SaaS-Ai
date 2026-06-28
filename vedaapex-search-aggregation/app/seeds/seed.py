"""Database seeder for subscription plans and promo codes."""

from sqlmodel import Session, select
from app.db.session import engine
from app.models.token import SubscriptionPlan, PromoCode
from app.config.costs import SUBSCRIPTION_PLANS


def seed_database():
    print("[Seed] Seeding database...\n")

    # Ensure all tables are created
    from sqlmodel import SQLModel
    from app.models.user import User
    from app.models.token import (
        TokenWallet,
        TokenTransaction,
        AIGenerationHistory,
        SubscriptionPlan,
        UserSubscription,
        DailyReward,
        PromoCode,
        PromoCodeUsage,
        UserSession,
        RequestLog,
    )

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Seed plans
        print("[Seed] Seeding subscription plans...")
        for i, (key, plan) in enumerate(SUBSCRIPTION_PLANS.items()):
            existing = session.exec(
                select(SubscriptionPlan).where(SubscriptionPlan.slug == plan["slug"])
            ).first()
            if existing:
                existing.name = plan["name"]
                existing.price = plan["price"]
                existing.token_allocation = plan["token_allocation"]
                existing.daily_credits = plan["daily_credits"]
                existing.features = plan["features"]
                existing.sort_order = i
                session.add(existing)
            else:
                session.add(
                    SubscriptionPlan(
                        name=plan["name"],
                        slug=plan["slug"],
                        price=plan["price"],
                        token_allocation=plan["token_allocation"],
                        daily_credits=plan["daily_credits"],
                        features=plan["features"],
                        sort_order=i,
                    )
                )
            print(f"  [Plan] {plan['name']} plan")

        # Seed promo codes
        print("\n[Seed] Seeding promo codes...")
        promos = [
            {"code": "WELCOME2026", "credits": 50, "max_uses": 1000},
            {"code": "VEDAAPEX100", "credits": 100, "max_uses": 500},
            {"code": "AIPOWER", "credits": 200, "max_uses": 100},
        ]
        for p in promos:
            existing = session.exec(select(PromoCode).where(PromoCode.code == p["code"])).first()
            if not existing:
                session.add(PromoCode(**p))
            print(f"  [Promo] {p['code']} ({p['credits']} credits)")

        session.commit()
        print("\n[Seed] Database seeding complete!\n")


if __name__ == "__main__":
    seed_database()
