from __future__ import annotations

from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    plan: str = Field(default="free")
    is_pro: bool = Field(default=False)
    subscription_start: Optional[datetime] = Field(default=None)
    subscription_end: Optional[datetime] = Field(default=None)
    provider: Optional[str] = Field(default=None, index=True)  # e.g. "google" or "github"
    provider_id: Optional[str] = Field(default=None, index=True)  # provider's subject/id

    # Existing relationships
    subscription: "Subscription" = Relationship(back_populates="user")
    generations: List["Generation"] = Relationship(back_populates="user")

    # Token system relationships
    wallet: "TokenWallet" = Relationship(back_populates="user")
    transactions: List["TokenTransaction"] = Relationship(back_populates="user")
    generation_history: List["AIGenerationHistory"] = Relationship(back_populates="user")
    user_subscription: "UserSubscription" = Relationship(back_populates="user")
    daily_rewards: List["DailyReward"] = Relationship(back_populates="user")
    promo_usages: List["PromoCodeUsage"] = Relationship(back_populates="user")
    sessions: List["UserSession"] = Relationship(back_populates="user")
    api_keys: List["APIKey"] = Relationship(back_populates="user")
    api_usage: List["APIUsage"] = Relationship(back_populates="user")


class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    plan: str = "Free"  # Free, Pro, Max, Ultra
    status: str = "active"
    current_period_end: Optional[datetime] = None

    user: User = Relationship(back_populates="subscription")


class Generation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    type: str  # text, image, video, ppt, etc.
    prompt: str
    output_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: User = Relationship(back_populates="generations")
