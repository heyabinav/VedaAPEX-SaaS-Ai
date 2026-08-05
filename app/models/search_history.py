from __future__ import annotations

from utils.time import utcnow

"""Database model for user search history entries."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

class SearchHistory(SQLModel, table=True):
    __tablename__ = "search_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = Field(index=True, max_length=120)
    query: str = Field(index=True)
    source: Optional[str] = Field(default=None, index=True)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
