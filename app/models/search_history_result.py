from __future__ import annotations

from utils.time import utcnow

"""Database model for stored search result payloads."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

class SearchHistoryResult(SQLModel, table=True):
    __tablename__ = "search_history_result"

    id: Optional[int] = Field(default=None, primary_key=True)
    history_id: int = Field(foreign_key="search_history.id", index=True, unique=True)
    result_count: int = Field(default=0)
    results_json: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utcnow)
