"""Database model for user-defined Custom Skills.

Allows VedaApex users to register personalized skills with trigger keywords,
custom system prompt instructions, and tool configurations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

from app.utils.time import utcnow


class UserCustomSkill(SQLModel, table=True):
    __tablename__ = "mcp_user_skills"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(index=True)
    slug: str = Field(index=True)
    description: str = Field(default="")
    trigger_keywords: str = Field(default="[]")  # JSON string list of trigger phrases
    instructions: str = Field(default="")  # Detailed system prompt rules / behavioral instructions
    tools_config: str = Field(default="{}")  # JSON string of associated tool/API config
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
