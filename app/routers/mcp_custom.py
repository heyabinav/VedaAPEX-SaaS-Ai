"""API Router for Custom MCP Connectors.

All endpoints adhere strictly to multi-tenant security:
- Connectors belong to exactly one authenticated user (user.id derived from auth token)
- Never trust user_id from request body
- Tokens are encrypted at rest and never exposed to the frontend or in logs
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.db.session import get_session
from app.models.mcp_connector import (
    MCPConnector,
    MCPOAuthCredential,
    MCPOAuthSession,
    MCPToolPermission,
)
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.schemas.mcp_custom import (
    MCPConnectRequest,
    MCPConnectResponse,
    MCPConnectorListResponse,
    MCPConnectorResponse,
    MCPConnectorUpdateRequest,
    MCPTestResponse,
    MCPToolCallRequest,
    MCPToolCallResponse,
    MCPToolSchema,
)
from app.services.mcp.client import MCPClientManager
from app.services.mcp.discovery import MCPDiscoveryService
from app.services.mcp.errors import (
    MCPAuthRequired,
    MCPConnectorNotFound,
    MCPConnectorUnauthorized,
    MCPOAuthDenied,
    MCPOAuthStateInvalid,
    MCPReauthRequired,
    MCPToolCallFailed,
    MCPToolNotFound,
)
from app.services.mcp.oauth import (
    MCPOAuthService,
    generate_pkce,
    generate_state,
    hash_state,
)
from app.services.mcp.security import validate_mcp_url
from app.services.mcp.tools import MCPToolProcessor
from app.services.secret_vault import decrypt_text, encrypt_text
from app.utils.time import utcnow

logger = logging.getLogger("mcp.custom_router")

router = APIRouter(prefix="/mcp", tags=["Custom MCP Connectors"])


# Helper: Get user connector & enforce multi-tenant authorization
def _get_user_connector(session: Session, user: User, connector_id: int) -> MCPConnector:
    connector = session.get(MCPConnector, connector_id)
    if not connector:
        raise MCPConnectorNotFound(f"Connector #{connector_id} not found")
    if connector.user_id != user.id:
        raise MCPConnectorUnauthorized("You are not authorized to access this connector")
    return connector


# Helper: Helper to convert connector model to response schema
def _to_connector_response(connector: MCPConnector) -> MCPConnectorResponse:
    tools_raw = json.loads(connector.tools_cache or "[]")
    tools = [
        MCPToolSchema(
            name=t.get("name", ""),
            description=t.get("description", ""),
            inputSchema=t.get("inputSchema", {}),
            permission=t.get("permission", "READ"),
        )
        for t in tools_raw
        if isinstance(t, dict) and t.get("name")
    ]
    capabilities = json.loads(connector.server_capabilities or "{}")

    return MCPConnectorResponse(
        id=connector.id or 0,
        user_id=connector.user_id,
        name=connector.name,
        mcp_url=connector.mcp_url,
        transport=connector.transport,
        auth_type=connector.auth_type,
        status=connector.status,
        server_name=connector.server_name,
        server_version=connector.server_version,
        server_capabilities=capabilities,
        tools_count=len(tools),
        tools=tools,
        created_at=connector.created_at,
        updated_at=connector.updated_at,
        last_connected_at=connector.last_connected_at,
        last_error=connector.last_error,
    )


# Helper: Perform tool discovery and update connector DB record
async def _do_tool_discovery(
    session: Session,
    connector: MCPConnector,
    auth_headers: Optional[Dict[str, str]] = None,
) -> int:
    client_mgr = MCPClientManager(connector.mcp_url, auth_headers=auth_headers, transport=connector.transport)
    server_info, tools_raw, resources_raw, prompts_raw = await client_mgr.discover_all()

    processed_tools = MCPToolProcessor.process_tools(tools_raw)

    connector.server_name = server_info.get("server_name")
    connector.server_version = server_info.get("server_version")
    connector.server_capabilities = json.dumps(server_info.get("capabilities", {}))
    connector.server_instructions = server_info.get("instructions")
    connector.tools_cache = json.dumps(processed_tools)
    connector.resources_cache = json.dumps(resources_raw)
    connector.prompts_cache = json.dumps(prompts_raw)
    connector.transport = server_info.get("transport", connector.transport)
    connector.status = "ACTIVE"
    connector.last_connected_at = utcnow()
    connector.last_error = None
    connector.updated_at = utcnow()

    session.add(connector)
    session.commit()
    session.refresh(connector)

    logger.info("Discovered %d tools for connector #%d (%s)", len(processed_tools), connector.id, connector.name)
    return len(processed_tools)


# Helper: Get valid access token for connector (with auto-refresh)
async def _get_auth_headers_for_connector(
    session: Session,
    connector: MCPConnector,
) -> Dict[str, str]:
    if connector.auth_type != "oauth":
        return {}

    cred = session.exec(
        select(MCPOAuthCredential).where(MCPOAuthCredential.connector_id == connector.id)
    ).first()

    if not cred or not cred.encrypted_access_token:
        connector.status = "REAUTH_REQUIRED"
        session.add(connector)
        session.commit()
        raise MCPReauthRequired("No OAuth credentials found. Re-authorization required.")

    access_token = decrypt_text(cred.encrypted_access_token)
    refresh_token = decrypt_text(cred.encrypted_refresh_token)

    # Check if token is expired or close to expiring (within 60s)
    if cred.expires_at and utcnow() >= (cred.expires_at - timedelta(seconds=60)):
        if not refresh_token:
            connector.status = "REAUTH_REQUIRED"
            session.add(connector)
            session.commit()
            raise MCPReauthRequired("Access token expired and no refresh token available.")

        logger.info("Access token expired for connector #%d. Refreshing...", connector.id)
        try:
            as_url = cred.issuer or connector.mcp_url
            oauth_cfg = await MCPOAuthService.discover_oauth_config(as_url)
            new_tokens = await MCPOAuthService.refresh_tokens(
                token_endpoint=oauth_cfg["token_endpoint"],
                refresh_token=refresh_token,
                client_id="vedaapex_mcp_client",
            )

            cred.encrypted_access_token = encrypt_text(new_tokens["access_token"])
            if new_tokens.get("refresh_token"):
                cred.encrypted_refresh_token = encrypt_text(new_tokens["refresh_token"])
            cred.expires_at = new_tokens.get("expires_at")
            cred.updated_at = utcnow()
            session.add(cred)
            session.commit()

            access_token = new_tokens["access_token"]
            logger.info("Refreshed access token successfully for connector #%d", connector.id)
        except Exception as exc:
            logger.error("Token refresh failed for connector #%d: %s", connector.id, exc)
            connector.status = "REAUTH_REQUIRED"
            session.add(connector)
            session.commit()
            raise MCPReauthRequired("Token refresh failed. Re-authorization required.") from exc

    return {"Authorization": f"{cred.token_type} {access_token}"}


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.post("/connect", response_model=MCPConnectResponse)
async def connect_mcp(
    body: MCPConnectRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Start MCP connection flow.

    1. Validates & runs SSRF checks on the MCP URL
    2. Probes the remote server to determine auth requirement
    3. If no auth: connects, discovers tools, marks ACTIVE
    4. If OAuth: initializes OAuth session (PKCE, state) and returns authorization URL
    """
    clean_url = validate_mcp_url(body.mcp_url)

    # Create temporary/pending connector record
    connector = MCPConnector(
        user_id=user.id,
        name=body.name.strip(),
        mcp_url=clean_url,
        transport="streamable-http",
        auth_type="none",
        status="CONNECTING",
    )
    session.add(connector)
    session.commit()
    session.refresh(connector)

    try:
        auth_req = await MCPDiscoveryService.probe_authentication(clean_url)

        if not auth_req.auth_required:
            # 1. No auth required -> direct connect & discover tools
            connector.auth_type = "none"
            tools_count = await _do_tool_discovery(session, connector)
            return MCPConnectResponse(
                status="connected",
                connector_id=connector.id or 0,
                authentication="none",
                tools_count=tools_count,
            )

        # 2. OAuth required -> build authorization URL
        connector.auth_type = "oauth"
        connector.status = "OAUTH_REQUIRED"
        session.add(connector)
        session.commit()

        oauth_cfg = auth_req.oauth_config or await MCPOAuthService.discover_oauth_config(clean_url, auth_req.www_authenticate)

        # Generate state & PKCE
        state = generate_state()
        state_h = hash_state(state)
        verifier, challenge = generate_pkce()

        callback_url = getattr(settings, "MCP_OAUTH_CALLBACK_URL", None) or "http://localhost:8000/api/v1/mcp/oauth/callback"

        # Try dynamic client registration if endpoint present
        client_id = await MCPOAuthService.register_dynamic_client(
            oauth_cfg.get("registration_endpoint", ""),
            callback_url,
        ) or "vedaapex_mcp_client"

        # Save OAuth session
        oauth_session = MCPOAuthSession(
            user_id=user.id,
            connector_id=connector.id or 0,
            state_hash=state_h,
            encrypted_pkce_verifier=encrypt_text(verifier),
            authorization_server=oauth_cfg.get("issuer", clean_url),
            client_id=client_id,
            redirect_uri=callback_url,
            expires_at=utcnow() + timedelta(seconds=int(getattr(settings, "MCP_OAUTH_SESSION_EXPIRY_SECONDS", 600))),
        )
        session.add(oauth_session)
        session.commit()

        auth_url = MCPOAuthService.build_authorization_url(
            authorization_endpoint=oauth_cfg["authorization_endpoint"],
            client_id=client_id,
            redirect_uri=callback_url,
            state=state,
            code_challenge=challenge,
        )

        logger.info("OAuth required for connector #%d. Returning auth URL.", connector.id)
        return MCPConnectResponse(
            status="oauth_required",
            connector_id=connector.id or 0,
            authentication="oauth",
            authorization_url=auth_url,
        )

    except Exception as exc:
        connector.status = "ERROR"
        connector.last_error = str(exc)
        session.add(connector)
        session.commit()
        raise


@router.post("/discover")
async def discover_mcp(
    body: MCPConnectRequest,
    user: User = Depends(get_current_user_auth),
):
    """Probe an MCP server URL to discover capabilities and auth requirement without saving."""
    clean_url = validate_mcp_url(body.mcp_url)
    auth_req = await MCPDiscoveryService.probe_authentication(clean_url)
    return {
        "success": True,
        "mcp_url": clean_url,
        "auth_required": auth_req.auth_required,
        "auth_type": auth_req.auth_type,
    }


@router.get("/oauth/callback")
async def oauth_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
):
    """Handle OAuth 2.0 authorization code callback.

    Exchanges authorization code for access token, stores tokens securely encrypted,
    reconnects to MCP, discovers tools, and marks connector ACTIVE.
    """
    if error:
        logger.warning("OAuth authorization denied/failed: %s (%s)", error, error_description)
        raise MCPOAuthDenied(f"OAuth error: {error} - {error_description or ''}")

    if not state or not code:
        raise MCPOAuthStateInvalid("Missing state or code parameter")

    s_hash = hash_state(state)
    oauth_sess = session.exec(
        select(MCPOAuthSession).where(MCPOAuthSession.state_hash == s_hash)
    ).first()

    if not oauth_sess:
        raise MCPOAuthStateInvalid("Invalid state parameter or session expired")

    if utcnow() > oauth_sess.expires_at:
        session.delete(oauth_sess)
        session.commit()
        raise MCPOAuthStateInvalid("OAuth authorization session expired")

    connector = session.get(MCPConnector, oauth_sess.connector_id)
    if not connector:
        raise MCPConnectorNotFound("Connector record associated with OAuth session not found")

    verifier = decrypt_text(oauth_sess.encrypted_pkce_verifier)
    oauth_cfg = await MCPOAuthService.discover_oauth_config(connector.mcp_url)

    # Exchange code for tokens
    tokens = await MCPOAuthService.exchange_code_for_tokens(
        token_endpoint=oauth_cfg["token_endpoint"],
        code=code,
        redirect_uri=oauth_sess.redirect_uri,
        client_id=oauth_sess.client_id,
        code_verifier=verifier,
    )

    # Store encrypted tokens
    existing_cred = session.exec(
        select(MCPOAuthCredential).where(MCPOAuthCredential.connector_id == connector.id)
    ).first()

    if not existing_cred:
        existing_cred = MCPOAuthCredential(connector_id=connector.id or 0)

    existing_cred.encrypted_access_token = encrypt_text(tokens["access_token"])
    existing_cred.encrypted_refresh_token = encrypt_text(tokens.get("refresh_token") or "")
    existing_cred.token_type = tokens.get("token_type", "Bearer")
    existing_cred.expires_at = tokens.get("expires_at")
    existing_cred.scope = tokens.get("scope")
    existing_cred.issuer = oauth_cfg.get("issuer")
    existing_cred.updated_at = utcnow()

    session.add(existing_cred)
    session.delete(oauth_sess)  # One-time use cleanup
    session.commit()

    # Reconnect and discover tools
    auth_headers = {"Authorization": f"{tokens['token_type']} {tokens['access_token']}"}
    tools_count = await _do_tool_discovery(session, connector, auth_headers=auth_headers)

    logger.info("OAuth flow completed successfully for connector #%d (%s). Found %d tools.", connector.id, connector.name, tools_count)

    return {
        "success": True,
        "status": "connected",
        "connector_id": connector.id,
        "connector_name": connector.name,
        "tools_count": tools_count,
        "message": "OAuth connection successful. Connector is now ACTIVE.",
    }


@router.get("/connectors", response_model=MCPConnectorListResponse)
async def list_connectors(
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """List all custom MCP connectors for the authenticated user."""
    connectors = session.exec(
        select(MCPConnector)
        .where(MCPConnector.user_id == user.id)
        .order_by(MCPConnector.updated_at.desc())
    ).all()

    return MCPConnectorListResponse(
        success=True,
        connectors=[_to_connector_response(c) for c in connectors],
    )


@router.get("/connectors/{id}", response_model=MCPConnectorResponse)
async def get_connector(
    id: int,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Get details of a specific connector owned by the authenticated user."""
    connector = _get_user_connector(session, user, id)
    return _to_connector_response(connector)


@router.patch("/connectors/{id}", response_model=MCPConnectorResponse)
async def update_connector(
    id: int,
    body: MCPConnectorUpdateRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Update connector details (e.g. name)."""
    connector = _get_user_connector(session, user, id)
    if body.name:
        connector.name = body.name.strip()
        connector.updated_at = utcnow()
        session.add(connector)
        session.commit()
        session.refresh(connector)
    return _to_connector_response(connector)


@router.delete("/connectors/{id}")
async def delete_connector(
    id: int,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Delete a connector and associated OAuth credentials/sessions/permissions."""
    connector = _get_user_connector(session, user, id)

    # Clean up credentials, sessions, permissions
    creds = session.exec(select(MCPOAuthCredential).where(MCPOAuthCredential.connector_id == id)).all()
    for c in creds:
        session.delete(c)

    sess_list = session.exec(select(MCPOAuthSession).where(MCPOAuthSession.connector_id == id)).all()
    for s in sess_list:
        session.delete(s)

    perms = session.exec(select(MCPToolPermission).where(MCPToolPermission.connector_id == id)).all()
    for p in perms:
        session.delete(p)

    session.delete(connector)
    session.commit()

    logger.info("Deleted connector #%d for user_id=%d", id, user.id)
    return {"success": True, "message": f"Connector #{id} deleted successfully."}


@router.post("/connectors/{id}/test", response_model=MCPTestResponse)
async def test_connector(
    id: int,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Test connectivity to an existing MCP server."""
    connector = _get_user_connector(session, user, id)
    auth_headers = await _get_auth_headers_for_connector(session, connector)
    tools_count = await _do_tool_discovery(session, connector, auth_headers=auth_headers)

    return MCPTestResponse(
        success=True,
        status="ACTIVE",
        tools_count=tools_count,
        message=f"Successfully connected to MCP server. Discovered {tools_count} tools.",
    )


@router.post("/connectors/{id}/refresh-tools")
async def refresh_connector_tools(
    id: int,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Re-discover tools from the remote MCP server."""
    connector = _get_user_connector(session, user, id)
    auth_headers = await _get_auth_headers_for_connector(session, connector)
    tools_count = await _do_tool_discovery(session, connector, auth_headers=auth_headers)

    return {
        "success": True,
        "connector_id": connector.id,
        "tools_count": tools_count,
        "tools": json.loads(connector.tools_cache or "[]"),
    }


@router.get("/connectors/{id}/tools")
async def get_connector_tools(
    id: int,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """List tools for a specific connector."""
    connector = _get_user_connector(session, user, id)
    tools = json.loads(connector.tools_cache or "[]")
    return {
        "success": True,
        "connector_id": connector.id,
        "tools_count": len(tools),
        "tools": tools,
    }


@router.post("/connectors/{id}/tools/{tool_name}/call", response_model=MCPToolCallResponse)
async def call_connector_tool(
    id: int,
    tool_name: str,
    body: MCPToolCallRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Execute an MCP tool call securely.

    Verifies user ownership, connector ACTIVE status, tool existence, permissions,
    retrieves credentials, refreshes tokens if needed, and invokes the tool.
    """
    connector = _get_user_connector(session, user, id)

    if connector.status != "ACTIVE":
        raise MCPToolCallFailed(f"Connector is in status {connector.status}. Please reconnect first.")

    # Find tool definition
    tools = json.loads(connector.tools_cache or "[]")
    target_tool = next((t for t in tools if t.get("name") == tool_name), None)
    if not target_tool:
        raise MCPToolNotFound(f"Tool '{tool_name}' not found on connector #{id}")

    # Check permission classification (WRITE tools require user confirmation)
    perm = target_tool.get("permission", "READ")
    if perm == "WRITE":
        perm_rec = session.exec(
            select(MCPToolPermission).where(
                MCPToolPermission.user_id == user.id,
                MCPToolPermission.connector_id == id,
                MCPToolPermission.tool_name == tool_name,
            )
        ).first()

        if not perm_rec or perm_rec.permission == "confirm":
            logger.info("Tool '%s' requires confirmation before execution", tool_name)
            return MCPToolCallResponse(
                success=True,
                requires_confirmation=True,
                connector_id=id,
                tool_name=tool_name,
                arguments=body.arguments,
            )

        if perm_rec.permission == "deny":
            raise MCPToolCallFailed(f"Tool '{tool_name}' execution denied by user permission settings")

    # Retrieve valid auth headers
    auth_headers = await _get_auth_headers_for_connector(session, connector)

    # Call the tool
    client_mgr = MCPClientManager(connector.mcp_url, auth_headers=auth_headers, transport=connector.transport)
    result = await client_mgr.call_tool(tool_name, body.arguments)

    logger.info("Executed MCP tool '%s' on connector #%d successfully", tool_name, id)
    return MCPToolCallResponse(
        success=True,
        result=result,
        requires_confirmation=False,
    )


@router.post("/connectors/{id}/reconnect")
async def reconnect_connector(
    id: int,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Reconnect an existing connector."""
    connector = _get_user_connector(session, user, id)
    auth_req = await MCPDiscoveryService.probe_authentication(connector.mcp_url)

    if not auth_req.auth_required:
        connector.auth_type = "none"
        tools_count = await _do_tool_discovery(session, connector)
        return {
            "status": "connected",
            "connector_id": connector.id,
            "tools_count": tools_count,
        }

    # OAuth required
    connector.auth_type = "oauth"
    connector.status = "OAUTH_REQUIRED"
    session.add(connector)
    session.commit()

    oauth_cfg = auth_req.oauth_config or await MCPOAuthService.discover_oauth_config(connector.mcp_url)

    state = generate_state()
    state_h = hash_state(state)
    verifier, challenge = generate_pkce()
    callback_url = getattr(settings, "MCP_OAUTH_CALLBACK_URL", None) or "http://localhost:8000/api/v1/mcp/oauth/callback"

    client_id = await MCPOAuthService.register_dynamic_client(
        oauth_cfg.get("registration_endpoint", ""),
        callback_url,
    ) or "vedaapex_mcp_client"

    oauth_session = MCPOAuthSession(
        user_id=user.id,
        connector_id=connector.id or 0,
        state_hash=state_h,
        encrypted_pkce_verifier=encrypt_text(verifier),
        authorization_server=oauth_cfg.get("issuer", connector.mcp_url),
        client_id=client_id,
        redirect_uri=callback_url,
        expires_at=utcnow() + timedelta(seconds=int(getattr(settings, "MCP_OAUTH_SESSION_EXPIRY_SECONDS", 600))),
    )
    session.add(oauth_session)
    session.commit()

    auth_url = MCPOAuthService.build_authorization_url(
        authorization_endpoint=oauth_cfg["authorization_endpoint"],
        client_id=client_id,
        redirect_uri=callback_url,
        state=state,
        code_challenge=challenge,
    )

    return {
        "status": "oauth_required",
        "connector_id": connector.id,
        "authorization_url": auth_url,
    }
