from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(min_length=1)
    model: Optional[str] = "auto"
    context_limit: int = 12


class ChatMessageItem(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime


class ChatSessionCreateResponse(BaseModel):
    success: bool = True
    session_id: str
    title: str


class ChatAnswerResponse(BaseModel):
    success: bool = True
    session_id: str
    title: str
    answer: str
    history: list[ChatMessageItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatSessionListItem(BaseModel):
    id: str
    title: str
    last_message_at: Optional[datetime] = None
    created_at: datetime


class ChatSessionListResponse(BaseModel):
    success: bool = True
    items: list[ChatSessionListItem]
