"""APIKey model for managing API keys per user."""

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class APIKey(SQLModel, table=True):
    """
    API Key model for managing user API keys.

    - Stores hashed keys (raw secret never stored in DB)
    - Prefix for fast lookup and user visibility
    - Scopes for granular permission control
    - Revoked flag for key invalidation
    - Usage tracking (last_used_at)
    """

    __tablename__ = "api_key"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: Optional[str] = Field(default="Default key", description="User-friendly name")
    prefix: str = Field(
        index=True,
        description="Non-secret prefix for lookup (e.g. first 8 chars like 'vedaapex_')",
    )
    key_hash: str = Field(
        index=True,
        description="Hash of the raw key (bcrypt or argon2) — never expose this",
    )
    scopes: Optional[str] = Field(
        default="",
        description="CSV or JSON scopes (e.g. 'generate:text,generate:image')",
    )
    revoked: bool = Field(default=False, description="Is key revoked/disabled")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = Field(default=None)

    # Relationship back to user
    user: "User" = Relationship(back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, user_id={self.user_id}, prefix={self.prefix}, revoked={self.revoked})>"


class APIUsage(SQLModel, table=True):
    """
    Track API key usage for rate limiting and monitoring.

    - Each API call increments usage for the key
    - Used for billing, rate limiting, and analytics
    """

    __tablename__ = "api_usage"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    api_key_prefix: str = Field(index=True, description="Prefix of the API key used")
    endpoint: str = Field(index=True, description="API endpoint called")
    method: str = Field(description="HTTP method (GET, POST, etc)")
    status_code: int = Field(description="HTTP response status")
    response_time_ms: int = Field(description="Response time in milliseconds")
    tokens_used: int = Field(default=0, description="Tokens consumed by this request")
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationship back to user
    user: "User" = Relationship(back_populates="api_usage")

    def __repr__(self) -> str:
        return (
            f"<APIUsage(id={self.id}, user_id={self.user_id}, "
            f"endpoint={self.endpoint}, status={self.status_code})>"
        )
