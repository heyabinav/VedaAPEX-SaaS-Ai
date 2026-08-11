from __future__ import annotations

import json
from app.utils.time import utcnow
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class WebsiteRequirement(SQLModel, table=True):
    __tablename__ = "website_requirement"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    business_name: str
    website_type: Optional[str] = None
    target_audience: Optional[str] = None
    primary_objectives_json: str = Field(default="[]")
    desired_features_json: str = Field(default="[]")
    content_pages_json: str = Field(default="[]")
    preferred_style: Optional[str] = None
    budget: Optional[str] = None
    launch_timeline: Optional[str] = None
    additional_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    def primary_objectives(self) -> list[str]:
        return json.loads(self.primary_objectives_json or "[]")

    def desired_features(self) -> list[str]:
        return json.loads(self.desired_features_json or "[]")

    def content_pages(self) -> list[str]:
        return json.loads(self.content_pages_json or "[]")
