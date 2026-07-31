"""Pydantic schemas for the Connectors system."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConnectorConfig(BaseModel):
    provider: str
    client_id: str
    client_secret: str
    redirect_uri: str
    auth_url: str
    token_url: str
    scopes: List[str] = []
    api_base_url: Optional[str] = None
    extra_params: Dict[str, str] = {}


class OAuthTokens(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    token_type: Optional[str] = None


class ConnectorStatus(BaseModel):
    success: bool = True
    provider: str
    connected: bool
    valid: bool = False
    expires_at: Optional[datetime] = None
    scopes: Optional[str] = None


class ConnectorLoginResponse(BaseModel):
    success: bool = True
    provider: str
    auth_url: str
    state: str


class ConnectorCallbackResponse(BaseModel):
    success: bool = True
    provider: str
    message: str


class ConnectorDisconnectResponse(BaseModel):
    success: bool = True
    provider: str
    message: str


class ConnectorError(BaseModel):
    success: bool = False
    provider: str
    error: str
    detail: Optional[str] = None
    status_code: int = 500
