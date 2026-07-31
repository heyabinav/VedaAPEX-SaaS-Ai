"""Admin-only managed connector registry endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.schemas.connector_management import (
    ManagedConnectorAuthScaffold,
    ManagedConnectorCreate,
    ManagedConnectorResponse,
    ManagedConnectorToolCall,
    ManagedConnectorToolCallResult,
    ManagedConnectorUpdate,
    ManagedConnectorValidationRequest,
    ManagedConnectorValidationResult,
)
from app.services.connector_management_service import ConnectorManagementService

logger = logging.getLogger("routers.connector_registry")
router = APIRouter(prefix="/connectors/registry", tags=["Managed Connectors"])


def admin_only(user: User = Depends(get_current_user_auth)) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


@router.get("", response_model=list[ManagedConnectorResponse])
async def list_managed_connectors(
    include_inactive: bool = False,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    return ConnectorManagementService.list_connectors(session, admin, include_inactive=include_inactive)


@router.post("", response_model=ManagedConnectorResponse)
async def create_managed_connector(
    body: ManagedConnectorCreate,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    return ConnectorManagementService.create_connector(session, admin, body)


@router.get("/{connector_id}", response_model=ManagedConnectorResponse)
async def get_managed_connector(
    connector_id: int,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    return ConnectorManagementService.get_connector_response(session, admin, connector_id)


@router.patch("/{connector_id}", response_model=ManagedConnectorResponse)
async def update_managed_connector(
    connector_id: int,
    body: ManagedConnectorUpdate,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    return ConnectorManagementService.update_connector(session, admin, connector_id, body)


@router.delete("/{connector_id}")
async def delete_managed_connector(
    connector_id: int,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    ConnectorManagementService.delete_connector(session, admin, connector_id)
    return {"success": True, "message": "Managed connector deleted"}


@router.post("/{connector_id}/validate", response_model=ManagedConnectorValidationResult)
async def validate_managed_connector(
    connector_id: int,
    body: ManagedConnectorValidationRequest,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    return await ConnectorManagementService.validate_mcp_connector(
        session,
        admin,
        connector_id,
        refresh_tools=body.refresh_tools,
    )


@router.post(
    "/{connector_id}/tools/{tool_name}/call",
    response_model=ManagedConnectorToolCallResult,
)
async def call_managed_connector_tool(
    connector_id: int,
    tool_name: str,
    body: ManagedConnectorToolCall,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    return await ConnectorManagementService.call_mcp_tool(
        session,
        admin,
        connector_id,
        tool_name,
        body.arguments,
    )


@router.get("/auth/scaffold/{auth_type}", response_model=ManagedConnectorAuthScaffold)
async def connector_auth_scaffold(auth_type: str, admin: User = Depends(admin_only)):
    del admin
    return ConnectorManagementService.get_auth_scaffold(auth_type)
