from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class UserOAuthToken(SQLModel, table=True):
    __tablename__ = "user_oauth_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    platform: str = Field(index=True)
    access_token: str = Field(default="")
    refresh_token: str = Field(default="")
    expires_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
