from utils.time import utcnow

from typing import TYPE_CHECKING, Any, Optional, List
from sqlalchemy.orm import relationship
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from enum import Enum


# ─── Enums ───────────────────────────────────────────────
class TransactionType(str, Enum):
    PURCHASE = "PURCHASE"
    USAGE = "USAGE"
    REFERRAL_BONUS = "REFERRAL_BONUS"
    DAILY_REWARD = "DAILY_REWARD"
    ADMIN_CREDIT = "ADMIN_CREDIT"
    ADMIN_DEBIT = "ADMIN_DEBIT"
    PROMO_CODE = "PROMO_CODE"
    SIGNUP_BONUS = "SIGNUP_BONUS"
    REFUND = "REFUND"


class GenerationType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    PPT = "PPT"
    MODEL_3D = "MODEL_3D"
    BG_REMOVAL = "BG_REMOVAL"
    TEXT = "TEXT"
    TTS = "TTS"


class GenerationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


class PaymentOrderStatus(str, Enum):
    CREATED = "CREATED"
    PAID = "PAID"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


# ─── Token Wallet ────────────────────────────────────────
class TokenWallet(SQLModel, table=True):
    __tablename__ = "token_wallet"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    balance: int = Field(default=100)
    lifetime_earned: int = Field(default=100)
    lifetime_spent: int = Field(default=0)
    updated_at: datetime = Field(default_factory=utcnow)

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="wallet")
    )


# ─── Token Transactions ─────────────────────────────────
class TokenTransaction(SQLModel, table=True):
    __tablename__ = "token_transaction"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    amount: int  # Positive = credit, Negative = debit
    type: str  # TransactionType value
    description: Optional[str] = None
    balance_after: int
    metadata_json: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="transactions")
    )


# ─── AI Generation History ───────────────────────────────
class AIGenerationHistory(SQLModel, table=True):
    __tablename__ = "ai_generation_history"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    type: str  # GenerationType value
    prompt: str
    output_url: Optional[str] = None
    cost: int
    status: str = Field(default=GenerationStatus.SUCCESS)
    provider: Optional[str] = None
    model_used: Optional[str] = None
    ip_address: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow)

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="generation_history")
    )


# ─── Subscription Plans ──────────────────────────────────
class SubscriptionPlan(SQLModel, table=True):
    __tablename__ = "subscription_plan"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    slug: str = Field(unique=True)
    price: float
    currency: str = Field(default="INR")
    billing_cycle: str = Field(default="monthly")
    token_allocation: int
    daily_credits: int = Field(default=0)
    features: str = ""  # JSON string
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow)

    user_subscriptions: Any = Relationship(
        sa_relationship=relationship("UserSubscription", back_populates="plan")
    )


# ─── User Subscriptions ─────────────────────────────────
class UserSubscription(SQLModel, table=True):
    __tablename__ = "user_subscription"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    plan_id: int = Field(foreign_key="subscription_plan.id")
    status: str = Field(default="active")
    current_period_start: datetime = Field(default_factory=utcnow)
    current_period_end: datetime
    payment_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="user_subscription")
    )
    plan: Any = Relationship(
        sa_relationship=relationship("SubscriptionPlan", back_populates="user_subscriptions")
    )


# ─── Daily Rewards ───────────────────────────────────────
class DailyReward(SQLModel, table=True):
    __tablename__ = "daily_reward"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    amount: int
    streak: int = Field(default=1)
    claimed_at: datetime = Field(default_factory=utcnow)

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="daily_rewards")
    )


# ─── Promo Codes ─────────────────────────────────────────
class PromoCode(SQLModel, table=True):
    __tablename__ = "promo_code"
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    credits: int
    max_uses: int = Field(default=100)
    current_uses: int = Field(default=0)
    expires_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)

    usages: Any = Relationship(
        sa_relationship=relationship("PromoCodeUsage", back_populates="promo_code")
    )


class PromoCodeUsage(SQLModel, table=True):
    __tablename__ = "promo_code_usage"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    promo_code_id: int = Field(foreign_key="promo_code.id")
    credits_awarded: int
    created_at: datetime = Field(default_factory=utcnow)

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="promo_usages")
    )
    promo_code: Any = Relationship(
        sa_relationship=relationship("PromoCode", back_populates="usages")
    )


# ─── User Sessions ───────────────────────────────────────
class UserSession(SQLModel, table=True):
    __tablename__ = "user_session"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=utcnow)

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="sessions")
    )


# ─── Request Log ─────────────────────────────────────────
class RequestLog(SQLModel, table=True):
    __tablename__ = "request_log"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = None
    endpoint: str
    method: str
    ip_address: str
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow)


# ─── API Keys ────────────────────────────────────────────
class APIKey(SQLModel, table=True):
    __tablename__ = "api_key"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(default="Default Key")
    key_hash: str = Field(unique=True, index=True)
    prefix: str = Field(index=True)  # First 8 chars for display
    is_active: bool = Field(default=True)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="api_keys")
    )


# ─── API Usage Tracking ─────────────────────────────────
class APIUsage(SQLModel, table=True):
    __tablename__ = "api_usage"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    tool_type: str = Field(index=True)  # text, image, video, etc.
    count: int = Field(default=0)
    date: str = Field(index=True)  # YYYY-MM-DD
    last_requested_at: datetime = Field(default_factory=utcnow)

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="api_usage")
    )


# ─── Payments ────────────────────────────────────────────────────────────
class PaymentOrder(SQLModel, table=True):
    __tablename__ = "payment_order"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    plan_id: int = Field(foreign_key="subscription_plan.id", index=True)
    provider: str = Field(default="RAZORPAY")
    order_id: str = Field(unique=True, index=True)
    receipt: str = Field(index=True)
    amount_paise: int
    currency: str = Field(default="INR")
    purpose: Optional[str] = None
    status: str = Field(default=PaymentOrderStatus.CREATED)
    notes_json: Optional[str] = None
    provider_payload_json: Optional[str] = None
    payment_id: Optional[str] = None
    signature: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    paid_at: Optional[datetime] = None

    transaction: Any = Relationship(
        sa_relationship=relationship("PaymentTransaction", back_populates="payment_order", uselist=False)
    )


class PaymentTransaction(SQLModel, table=True):
    __tablename__ = "payment_transaction"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    payment_order_id: int = Field(foreign_key="payment_order.id", unique=True, index=True)
    provider: str = Field(default="RAZORPAY")
    payment_id: str = Field(index=True)
    order_id: str = Field(index=True)
    signature: Optional[str] = None
    status: str = Field(default=PaymentStatus.VERIFIED)
    amount_paise: int
    currency: str = Field(default="INR")
    metadata_json: Optional[str] = None
    provider_payload_json: Optional[str] = None
    verified_at: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)

    payment_order: Any = Relationship(
        sa_relationship=relationship("PaymentOrder", back_populates="transaction")
    )



TokenWallet.model_rebuild()
TokenTransaction.model_rebuild()
AIGenerationHistory.model_rebuild()
UserSubscription.model_rebuild()
DailyReward.model_rebuild()
PromoCodeUsage.model_rebuild()
UserSession.model_rebuild()
APIKey.model_rebuild()
APIUsage.model_rebuild()
PaymentOrder.model_rebuild()
PaymentTransaction.model_rebuild()