"""Schemas for managed MCP connector administration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


ConnectorAuthType = Literal["none", "api_key", "bearer", "oauth2"]
ConnectorTransport = Literal["streamable-http", "sse", "http"]


class ManagedConnectorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    icon_url: Optional[str] = Field(default=None, max_length=2048)
    server_url: str = Field(..., min_length=8, max_length=2048)
    discovery_path: str = Field(default="/mcp", max_length=128)
    transport: ConnectorTransport = "streamable-http"
    auth_type: ConnectorAuthType = "none"
    auth_config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("server_url")
    @classmethod
    def _clean_server_url(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        parsed = urlparse(cleaned)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("server_url must include a valid scheme and host")
        return cleaned

    @field_validator("discovery_path")
    @classmethod
    def _clean_discovery_path(cls, value: str) -> str:
        cleaned = "/" + value.strip().lstrip("/")
        return cleaned or "/mcp"

    @model_validator(mode="after")
    def _validate_auth_config(self):
        auth_type = self.auth_type
        config = self.auth_config or {}

        if auth_type == "api_key" and not config.get("api_key_header"):
            raise ValueError("api_key auth requires api_key_header")
        if auth_type == "bearer" and not config.get("header_name", "Authorization"):
            raise ValueError("bearer auth requires header_name or Authorization")
        if auth_type == "oauth2":
            missing = [
                key
                for key in ("authorization_url", "token_url", "client_id", "redirect_uri")
                if not config.get(key)
            ]
            if missing:
                raise ValueError(f"oauth2 auth requires: {', '.join(missing)}")

        return self


class ManagedConnectorCreate(ManagedConnectorBase):
    pass


class ManagedConnectorUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    icon_url: Optional[str] = Field(default=None, max_length=2048)
    server_url: Optional[str] = Field(default=None, min_length=8, max_length=2048)
    discovery_path: Optional[str] = Field(default=None, max_length=128)
    transport: Optional[ConnectorTransport] = None
    auth_type: Optional[ConnectorAuthType] = None
    auth_config: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value is not None else value

    @field_validator("server_url")
    @classmethod
    def _clean_server_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip().rstrip("/")
        parsed = urlparse(cleaned)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("server_url must include a valid scheme and host")
        return cleaned

    @field_validator("discovery_path")
    @classmethod
    def _clean_discovery_path(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return "/" + value.strip().lstrip("/")


class ManagedConnectorTool(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    method: Optional[str] = None
    path: Optional[str] = None


class ManagedConnectorResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    icon_url: Optional[str] = None
    server_url: str
    discovery_path: str
    transport: str
    auth_type: str
    auth_config_preview: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    discovered_tools: list[ManagedConnectorTool] = Field(default_factory=list)
    is_active: bool
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
    last_validated_at: Optional[datetime] = None
    validation_status: str
    validation_error: Optional[str] = None
    last_validation_http_status: Optional[int] = None
    tool_count: int = 0


class ManagedConnectorValidationRequest(BaseModel):
    refresh_tools: bool = True


class ManagedConnectorValidationResult(BaseModel):
    success: bool
    connector_id: int
    reachable: bool
    valid: bool
    validation_status: str
    http_status: Optional[int] = None
    discovery_url: Optional[str] = None
    tool_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    error: Optional[str] = None
    validated_at: datetime


class ManagedConnectorToolCall(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


class ManagedConnectorToolCallResult(BaseModel):
    connector_id: int
    tool_name: str
    result: Any
    http_status: int


class ManagedConnectorAuthScaffold(BaseModel):
    auth_type: ConnectorAuthType
    summary: str
    required_fields: list[str] = Field(default_factory=list)
    secrets_to_store: list[str] = Field(default_factory=list)
    example_config: dict[str, Any] = Field(default_factory=dict)
