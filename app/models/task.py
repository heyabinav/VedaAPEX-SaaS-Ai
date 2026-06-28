from __future__ import annotations

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class Task(SQLModel, table=True):
    __tablename__ = "media_task"

    id: str = Field(primary_key=True, index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    type: (
        str  # "enhance_image", "enhance_video", "remove_watermark_image", "remove_watermark_video"
    )
    status: str = Field(default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    progress: int = Field(default=0)  # 0 to 100
    input_path: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
