"""Database models for Custom MCP Connectors, OAuth credentials, OAuth sessions, and tool permissions.

Tables:
1. mcp_connectors
2. mcp_oauth_credentials
3. mcp_oauth_sessions
4. mcp_tool_permissions
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils.time import utcnow


class MCPConnector(SQLModel, table=True):
    __tablename__ = "mcp_connectors"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(index=True)
    mcp_url: str = Field(index=True)
    transport: str = Field(default="streamable-http")  # "streamable-http" or "sse"
    auth_type: str = Field(default="none", index=True)  # "none" or "oauth"
    status: str = Field(default="PENDING", index=True)  # PENDING, CONNECTING, OAUTH_REQUIRED, ACTIVE, DISCONNECTED, ERROR, REAUTH_REQUIRED
    server_name: Optional[str] = Field(default=None)
    server_version: Optional[str] = Field(default=None)
    server_capabilities: str = Field(default="{}")  # JSON string
    server_instructions: Optional[str] = Field(default=None)
    tools_cache: str = Field(default="[]")  # JSON string
    resources_cache: str = Field(default="[]")  # JSON string
    prompts_cache: str = Field(default="[]")  # JSON string
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_connected_at: Optional[datetime] = Field(default=None)
    last_error: Optional[str] = Field(default=None)


class MCPOAuthCredential(SQLModel, table=True):
    __tablename__ = "mcp_oauth_credentials"

    id: Optional[int] = Field(default=None, primary_key=True)
    connector_id: int = Field(foreign_key="mcp_connectors.id", index=True, unique=True)
    encrypted_access_token: str = Field(default="")
    encrypted_refresh_token: str = Field(default="")
    token_type: str = Field(default="Bearer")
    expires_at: Optional[datetime] = Field(default=None)
    scope: Optional[str] = Field(default=None)
    issuer: Optional[str] = Field(default=None)
    encryption_key_version: int = Field(default=1)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class MCPOAuthSession(SQLModel, table=True):
    __tablename__ = "mcp_oauth_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    connector_id: int = Field(foreign_key="mcp_connectors.id", index=True)
    state_hash: str = Field(index=True)
    encrypted_pkce_verifier: str = Field(default="")
    authorization_server: str = Field(default="")
    client_id: str = Field(default="")
    redirect_uri: str = Field(default="")
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)


class MCPToolPermission(SQLModel, table=True):
    __tablename__ = "mcp_tool_permissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    connector_id: int = Field(foreign_key="mcp_connectors.id", index=True)
    tool_name: str = Field(index=True)
    permission: str = Field(default="allow")  # "allow", "deny", "confirm"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
