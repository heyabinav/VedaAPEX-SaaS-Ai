from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_message"

    id: str = Field(primary_key=True, index=True)
    session_id: str = Field(foreign_key="chat_session.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = Field(index=True)  # user, assistant, system
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    metadata_json: str = Field(default="{}")
    tokens_used: Optional[int] = None
