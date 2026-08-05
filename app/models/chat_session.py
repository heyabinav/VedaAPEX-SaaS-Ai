from __future__ import annotations

from app.utils.time import utcnow

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_session"

    id: str = Field(primary_key=True, index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = Field(default="New Chat", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_message_at: Optional[datetime] = None
