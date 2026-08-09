"""Pydantic request and response schemas for Custom MCP Connectors API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MCPConnectRequest(BaseModel):
    name: str = Field(..., description="Connector name", min_length=1, max_length=100)
    mcp_url: str = Field(..., description="Remote MCP server URL (https://...)")


class MCPConnectResponse(BaseModel):
    status: str = Field(..., description="connected or oauth_required")
    connector_id: int = Field(..., description="Connector ID")
    authentication: str = Field(..., description="none or oauth")
    tools_count: Optional[int] = Field(default=0)
    authorization_url: Optional[str] = Field(default=None, description="OAuth authorization URL if OAuth required")


class MCPToolSchema(BaseModel):
    name: str
    description: str = ""
    inputSchema: Dict[str, Any] = Field(default_factory=dict)
    permission: str = "READ"  # "READ" or "WRITE"


class MCPConnectorResponse(BaseModel):
    id: int
    user_id: int
    name: str
    mcp_url: str
    transport: str
    auth_type: str
    status: str
    server_name: Optional[str] = None
    server_version: Optional[str] = None
    server_capabilities: Dict[str, Any] = Field(default_factory=dict)
    tools_count: int = 0
    tools: List[MCPToolSchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_connected_at: Optional[datetime] = None
    last_error: Optional[str] = None


class MCPConnectorListResponse(BaseModel):
    success: bool = True
    connectors: List[MCPConnectorResponse] = Field(default_factory=list)


class MCPConnectorUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)


class MCPToolCallRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    success: bool = True
    result: Any = None
    requires_confirmation: bool = False
    connector_id: Optional[int] = None
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None


class MCPTestResponse(BaseModel):
    success: bool
    status: str
    tools_count: int
    message: str
