from utils.time import utcnow

from typing import TYPE_CHECKING, Any, Optional, List
from sqlalchemy.orm import relationship
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

if TYPE_CHECKING:
    from app.models.token import (
        AIGenerationHistory,
        APIKey,
        APIUsage,
        DailyReward,
        PromoCodeUsage,
        TokenTransaction,
        TokenWallet,
        UserSession,
        UserSubscription,
    )


class UserBase(SQLModel):
    email: str = Field(index=True, unique=True)
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False


class User(UserBase, table=True):
    __tablename__ = "user"
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(default="")
    role: str = Field(default="USER")  # USER or ADMIN
    referral_code: str = Field(unique=True, index=True, default="")
    referred_by: Optional[str] = None
    api_key: Optional[str] = Field(default=None, unique=True, index=True)
    webhook_url: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)
    plan: str = Field(default="free")
    is_pro: bool = Field(default=False)
    subscription_start: Optional[datetime] = Field(default=None)
    subscription_end: Optional[datetime] = Field(default=None)
    provider: Optional[str] = Field(default=None, index=True)  # e.g. "google" or "github"
    provider_id: Optional[str] = Field(default=None, index=True)  # provider's subject/id
    canva_access_token: Optional[str] = Field(default=None)
    canva_refresh_token: Optional[str] = Field(default=None)
    canva_token_expires_at: Optional[datetime] = Field(default=None)
    figma_access_token: Optional[str] = Field(default=None)
    figma_refresh_token: Optional[str] = Field(default=None)
    figma_token_expires_at: Optional[datetime] = Field(default=None)

    # Existing relationships
    subscription: Any = Relationship(
        sa_relationship=relationship("Subscription", back_populates="user", uselist=False)
    )
    generations: Any = Relationship(
        sa_relationship=relationship("Generation", back_populates="user")
    )

    # Token system relationships
    wallet: Any = Relationship(
        sa_relationship=relationship("TokenWallet", back_populates="user", uselist=False)
    )
    transactions: Any = Relationship(
        sa_relationship=relationship("TokenTransaction", back_populates="user")
    )
    generation_history: Any = Relationship(
        sa_relationship=relationship("AIGenerationHistory", back_populates="user")
    )
    user_subscription: Any = Relationship(
        sa_relationship=relationship("UserSubscription", back_populates="user", uselist=False)
    )
    daily_rewards: Any = Relationship(
        sa_relationship=relationship("DailyReward", back_populates="user")
    )
    promo_usages: Any = Relationship(
        sa_relationship=relationship("PromoCodeUsage", back_populates="user")
    )
    sessions: Any = Relationship(
        sa_relationship=relationship("UserSession", back_populates="user")
    )
    api_keys: Any = Relationship(
        sa_relationship=relationship("APIKey", back_populates="user")
    )
    api_usage: Any = Relationship(
        sa_relationship=relationship("APIUsage", back_populates="user")
    )


class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    plan: str = "Free"  # Free, Pro, Max, Ultra
    status: str = "active"
    current_period_end: Optional[datetime] = None

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="subscription")
    )


class Generation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    type: str  # text, image, video, ppt, etc.
    prompt: str
    output_url: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    user: Any = Relationship(
        sa_relationship=relationship("User", back_populates="generations")
    )