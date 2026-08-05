from __future__ import annotations

from app.utils.time import utcnow

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Task(SQLModel, table=True):
    __tablename__ = "media_task"

    id: str = Field(primary_key=True, index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    type: str = Field(
        index=True
    )  # "enhance_image", "enhance_video", "remove_watermark_image", "remove_watermark_video"
    status: str = Field(default="PENDING", index=True)  # PENDING, PROCESSING, COMPLETED, FAILED
    progress: int = Field(default=0, index=True)  # 0 to 100
    input_path: str
    options_json: str = Field(default="{}")
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
