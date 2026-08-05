"""Database model for user-managed MCP connectors."""

from __future__ import annotations

from utils.time import utcnow

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

class ManagedConnector(SQLModel, table=True):
    __tablename__ = "managed_connector"

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str = Field(index=True)
    description: str = Field(default="")
    icon_url: Optional[str] = None
    server_url: str = Field(index=True)
    discovery_path: str = Field(default="/mcp")
    transport: str = Field(default="streamable-http")
    auth_type: str = Field(default="none", index=True)
    auth_config_encrypted: str = Field(default="")
    metadata_json: str = Field(default="{}")
    discovered_tools_json: str = Field(default="[]")
    is_active: bool = Field(default=True, index=True)
    created_by_user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_validated_at: Optional[datetime] = None
    validation_status: str = Field(default="pending", index=True)
    validation_error: Optional[str] = None
    last_validation_http_status: Optional[int] = None
    tool_count: int = Field(default=0)
