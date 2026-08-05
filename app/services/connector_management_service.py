"""Managed connector storage, validation, and auth scaffolding."""

from __future__ import annotations

from utils.time import utcnow

import ipaddress
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.models.managed_connector import ManagedConnector
from app.models.user import User
from app.schemas.connector_management import (
    ManagedConnectorAuthScaffold,
    ManagedConnectorCreate,
    ManagedConnectorResponse,
    ManagedConnectorTool,
    ManagedConnectorUpdate,
    ManagedConnectorValidationResult,
)
from app.services.secret_vault import decrypt_json, encrypt_json, mask_secret
from app.services.mcp_client import MCPClientError, StreamableHTTPMCPClient

logger = logging.getLogger("services.connector_management")

ALLOWED_AUTH_TYPES = {"none", "api_key", "bearer", "oauth2"}
ALLOWED_TRANSPORTS = {"streamable-http", "sse", "http"}

def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "connector"

def _unique_slug(session: Session, base_slug: str, current_id: Optional[int] = None) -> str:
    slug = base_slug
    suffix = 1
    while True:
        existing = session.exec(select(ManagedConnector).where(ManagedConnector.slug == slug)).first()
        if not existing or existing.id == current_id:
            return slug
        suffix += 1
        slug = f"{base_slug}-{suffix}"

def _parse_json_field(value: str, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default

def _as_json(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value or {}, ensure_ascii=True, separators=(",", ":"))

def _public_auth_preview(auth_type: str, auth_config: dict[str, Any]) -> dict[str, Any]:
    if not auth_config:
        return {}

    preview = dict(auth_config)
    for key in {
        "client_secret",
        "api_key",
        "access_token",
        "refresh_token",
        "secret",
        "token",
        "private_key",
    }:
        if key in preview:
            preview[key] = mask_secret(str(preview[key]))

    if auth_type == "oauth2":
        preview.setdefault("grant_type", "authorization_code")

    return preview

def _normalize_server_url(server_url: str) -> str:
    parsed = urlparse(server_url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="server_url must use http or https")
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="server_url must include a hostname")

    host = (parsed.hostname or "").lower()
    if settings.APP_ENV != "development":
        if parsed.scheme != "https":
            raise HTTPException(status_code=400, detail="Production connectors must use https")
        if host in {"localhost", "127.0.0.1", "::1"}:
            raise HTTPException(status_code=400, detail="Localhost connectors are only allowed in development")
        try:
            if host:
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise HTTPException(status_code=400, detail="Private IP connector targets are blocked in production")
        except ValueError:
            pass

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}".rstrip("/")

def _validate_auth_config(auth_type: str, auth_config: dict[str, Any]) -> None:
    if auth_type not in ALLOWED_AUTH_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported auth_type: {auth_type}")

    if auth_type == "api_key" and not auth_config.get("api_key_header"):
        raise HTTPException(status_code=400, detail="api_key auth requires api_key_header")

    if auth_type == "bearer" and not auth_config.get("header_name"):
        auth_config["header_name"] = "Authorization"

    if auth_type == "oauth2":
        missing = [
            key
            for key in ("authorization_url", "token_url", "client_id", "redirect_uri")
            if not auth_config.get(key)
        ]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"oauth2 auth requires: {', '.join(missing)}",
            )

def _connector_to_response(connector: ManagedConnector) -> ManagedConnectorResponse:
    auth_config = decrypt_json(connector.auth_config_encrypted)
    tools = [
        ManagedConnectorTool(**tool)
        for tool in _parse_json_field(connector.discovered_tools_json, [])
        if isinstance(tool, dict) and tool.get("name")
    ]

    return ManagedConnectorResponse(
        id=connector.id or 0,
        slug=connector.slug,
        name=connector.name,
        description=connector.description,
        icon_url=connector.icon_url,
        server_url=connector.server_url,
        discovery_path=connector.discovery_path,
        transport=connector.transport,
        auth_type=connector.auth_type,
        auth_config_preview=_public_auth_preview(connector.auth_type, auth_config),
        metadata=_parse_json_field(connector.metadata_json, {}),
        discovered_tools=tools,
        is_active=connector.is_active,
        created_by_user_id=connector.created_by_user_id,
        created_at=connector.created_at,
        updated_at=connector.updated_at,
        last_validated_at=connector.last_validated_at,
        validation_status=connector.validation_status,
        validation_error=connector.validation_error,
        last_validation_http_status=connector.last_validation_http_status,
        tool_count=connector.tool_count,
    )

class ConnectorManagementService:
    @staticmethod
    def list_connectors(session: Session, user: User, include_inactive: bool = False) -> list[ManagedConnectorResponse]:
        query = select(ManagedConnector).where(ManagedConnector.created_by_user_id == user.id)
        if not include_inactive:
            query = query.where(ManagedConnector.is_active == True)  # noqa: E712
        connectors = session.exec(query.order_by(ManagedConnector.updated_at.desc())).all()
        return [_connector_to_response(connector) for connector in connectors]

    @staticmethod
    def get_connector(session: Session, user: User, connector_id: int) -> ManagedConnector:
        connector = session.get(ManagedConnector, connector_id)
        if not connector or connector.created_by_user_id != user.id:
            raise HTTPException(status_code=404, detail="Managed connector not found")
        return connector

    @staticmethod
    def create_connector(session: Session, user: User, body: ManagedConnectorCreate) -> ManagedConnectorResponse:
        server_url = _normalize_server_url(body.server_url)
        auth_config = dict(body.auth_config or {})
        _validate_auth_config(body.auth_type, auth_config)

        slug = _unique_slug(session, _slugify(body.name))

        connector = ManagedConnector(
            slug=slug,
            name=body.name,
            description=body.description,
            icon_url=body.icon_url,
            server_url=server_url,
            discovery_path=body.discovery_path,
            transport=body.transport,
            auth_type=body.auth_type,
            auth_config_encrypted=encrypt_json(auth_config),
            metadata_json=_as_json(body.metadata),
            discovered_tools_json="[]",
            is_active=body.is_active,
            created_by_user_id=user.id,
            created_at=utcnow(),
            updated_at=utcnow(),
            validation_status="pending",
        )
        session.add(connector)
        session.commit()
        session.refresh(connector)
        return _connector_to_response(connector)

    @staticmethod
    def update_connector(
        session: Session,
        user: User,
        connector_id: int,
        body: ManagedConnectorUpdate,
    ) -> ManagedConnectorResponse:
        connector = ConnectorManagementService.get_connector(session, user, connector_id)

        if body.name is not None:
            connector.name = body.name
            connector.slug = _unique_slug(session, _slugify(body.name), current_id=connector.id)
        if body.description is not None:
            connector.description = body.description
        if body.icon_url is not None:
            connector.icon_url = body.icon_url
        if body.server_url is not None:
            connector.server_url = _normalize_server_url(body.server_url)
        if body.discovery_path is not None:
            connector.discovery_path = "/" + body.discovery_path.strip().lstrip("/")
        if body.transport is not None:
            if body.transport not in ALLOWED_TRANSPORTS:
                raise HTTPException(status_code=400, detail=f"Unsupported transport: {body.transport}")
            connector.transport = body.transport
        if body.auth_type is not None:
            connector.auth_type = body.auth_type
        auth_config = decrypt_json(connector.auth_config_encrypted)
        if body.auth_config is not None:
            auth_config = dict(body.auth_config)
        if body.auth_type is not None or body.auth_config is not None:
            _validate_auth_config(connector.auth_type, auth_config)
            connector.auth_config_encrypted = encrypt_json(auth_config)
        if body.metadata is not None:
            connector.metadata_json = _as_json(body.metadata)
        if body.is_active is not None:
            connector.is_active = body.is_active

        connector.updated_at = utcnow()
        session.add(connector)
        session.commit()
        session.refresh(connector)
        return _connector_to_response(connector)

    @staticmethod
    def delete_connector(session: Session, user: User, connector_id: int) -> bool:
        connector = ConnectorManagementService.get_connector(session, user, connector_id)
        session.delete(connector)
        session.commit()
        return True

    @staticmethod
    def build_auth_scaffold(auth_type: str) -> ManagedConnectorAuthScaffold:
        if auth_type == "none":
            return ManagedConnectorAuthScaffold(
                auth_type="none",
                summary="No authentication. The connector endpoint is invoked without extra headers.",
                required_fields=[],
                secrets_to_store=[],
                example_config={"type": "none"},
            )
        if auth_type == "api_key":
            return ManagedConnectorAuthScaffold(
                auth_type="api_key",
                summary="Attach a static API key using a dedicated header.",
                required_fields=["api_key_header", "api_key"],
                secrets_to_store=["api_key"],
                example_config={
                    "type": "api_key",
                    "api_key_header": "X-API-Key",
                    "api_key_prefix": "",
                },
            )
        if auth_type == "bearer":
            return ManagedConnectorAuthScaffold(
                auth_type="bearer",
                summary="Send a bearer token in the Authorization header.",
                required_fields=["access_token"],
                secrets_to_store=["access_token", "refresh_token"],
                example_config={
                    "type": "bearer",
                    "header_name": "Authorization",
                    "scheme": "Bearer",
                },
            )
        if auth_type == "oauth2":
            return ManagedConnectorAuthScaffold(
                auth_type="oauth2",
                summary="Use OAuth 2.0 authorization code flow with encrypted token storage.",
                required_fields=["authorization_url", "token_url", "client_id", "redirect_uri"],
                secrets_to_store=["client_secret", "access_token", "refresh_token"],
                example_config={
                    "type": "oauth2",
                    "grant_type": "authorization_code",
                    "authorization_url": "https://provider.example/oauth/authorize",
                    "token_url": "https://provider.example/oauth/token",
                    "scopes": ["read:tools"],
                },
            )
        raise HTTPException(status_code=400, detail=f"Unsupported auth_type: {auth_type}")

    @staticmethod
    async def validate_connector(
        session: Session,
        user: User,
        connector_id: int,
        refresh_tools: bool = True,
    ) -> ManagedConnectorValidationResult:
        connector = ConnectorManagementService.get_connector(session, user, connector_id)
        discovery_path = connector.discovery_path or "/mcp"
        base_url = connector.server_url.rstrip("/")
        discovery_url = f"{base_url}{discovery_path}"
        warnings: list[str] = []
        tools: list[dict[str, Any]] = []
        reachable = False
        valid = False
        http_status: Optional[int] = None
        error: Optional[str] = None
        validation_status = "failed"

        transport = httpx.AsyncHTTPTransport(retries=1)
        timeout = httpx.Timeout(15.0, connect=5.0)

        try:
            async with httpx.AsyncClient(transport=transport, timeout=timeout, follow_redirects=True) as client:
                response = await client.get(
                    discovery_url,
                    headers={"Accept": "application/json, text/plain;q=0.9, */*;q=0.8"},
                )
                http_status = response.status_code
                reachable = response.status_code < 500

                if response.status_code >= 400:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Connector discovery failed with HTTP {response.status_code}",
                    )

                content_type = response.headers.get("content-type", "")
                payload: Any
                if "json" in content_type.lower():
                    try:
                        payload = response.json()
                    except ValueError:
                        payload = response.text
                        warnings.append("Discovery endpoint returned invalid JSON")
                else:
                    payload = response.text

                parsed_tools = ConnectorManagementService._extract_tools(payload)
                if parsed_tools:
                    tools = parsed_tools
                    valid = True
                    validation_status = "healthy"
                else:
                    warnings.append("No tool definitions were discovered from the endpoint")
                    valid = response.status_code < 400
                    validation_status = "limited"
        except httpx.HTTPError as exc:
            error = str(exc)
            logger.warning("Connector validation failed for connector_id=%s: %s", connector_id, error)
        except HTTPException as exc:
            error = str(exc.detail)
            logger.warning("Connector validation failed for connector_id=%s: %s", connector_id, error)
        finally:
            connector.last_validated_at = utcnow()
            connector.last_validation_http_status = http_status
            connector.validation_error = error
            connector.validation_status = validation_status if valid else "failed"
            connector.tool_count = len(tools)
            if refresh_tools:
                connector.discovered_tools_json = json.dumps(tools, ensure_ascii=True, separators=(",", ":"))
            connector.updated_at = utcnow()
            session.add(connector)
            session.commit()
            session.refresh(connector)

        return ManagedConnectorValidationResult(
            success=error is None,
            connector_id=connector.id or 0,
            reachable=reachable,
            valid=valid,
            validation_status=connector.validation_status,
            http_status=http_status,
            discovery_url=discovery_url,
            tool_count=len(tools),
            warnings=warnings,
            error=error,
            validated_at=connector.last_validated_at or utcnow(),
        )

    @staticmethod
    def _extract_tools(payload: Any) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []

        def _push(items: Any) -> None:
            if not isinstance(items, list):
                return
            for item in items:
                if isinstance(item, dict) and item.get("name"):
                    candidates.append(
                        {
                            "name": item.get("name"),
                            "description": item.get("description", ""),
                            "input_schema": item.get("inputSchema") or item.get("input_schema") or {},
                            "output_schema": item.get("outputSchema") or item.get("output_schema") or {},
                            "method": item.get("method"),
                            "path": item.get("path"),
                        }
                    )

        if isinstance(payload, dict):
            for key in ("tools", "capabilities", "available_tools", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    _push(value)
            if not candidates and isinstance(payload.get("data"), dict):
                nested = payload["data"]
                for key in ("tools", "capabilities", "items"):
                    value = nested.get(key)
                    if isinstance(value, list):
                        _push(value)
        elif isinstance(payload, list):
            _push(payload)

        return candidates

    @staticmethod
    def get_auth_scaffold(auth_type: str) -> ManagedConnectorAuthScaffold:
        return ConnectorManagementService.build_auth_scaffold(auth_type)

    @staticmethod
    def get_connector_response(session: Session, user: User, connector_id: int) -> ManagedConnectorResponse:
        connector = ConnectorManagementService.get_connector(session, user, connector_id)
        return _connector_to_response(connector)

    @staticmethod
    async def validate_mcp_connector(
        session: Session,
        user: User,
        connector_id: int,
        refresh_tools: bool = True,
    ) -> ManagedConnectorValidationResult:
        connector = ConnectorManagementService.get_connector(session, user, connector_id)
        if connector.transport != "streamable-http":
            return await ConnectorManagementService.validate_connector(
                session, user, connector_id, refresh_tools=refresh_tools
            )

        discovery_url = f"{connector.server_url.rstrip('/')}{connector.discovery_path or '/mcp'}"
        tools: list[dict[str, Any]] = []
        http_status: Optional[int] = None
        error: Optional[str] = None
        warnings: list[str] = []

        try:
            client = StreamableHTTPMCPClient(
                discovery_url,
                connector.auth_type,
                decrypt_json(connector.auth_config_encrypted),
            )
            discovery = await client.discover_tools()
            http_status = discovery.http_status
            tools = ConnectorManagementService._extract_tools({"tools": discovery.tools})
            if not tools:
                warnings.append("The MCP server is reachable but exposes no tools")
            connector.validation_status = "healthy"
            connector.validation_error = None
        except (MCPClientError, httpx.HTTPError) as exc:
            error = str(exc)
            connector.validation_status = "failed"
            connector.validation_error = error
            logger.warning("MCP validation failed for connector_id=%s: %s", connector_id, error)
        finally:
            connector.last_validated_at = utcnow()
            connector.last_validation_http_status = http_status
            connector.tool_count = len(tools)
            if refresh_tools:
                connector.discovered_tools_json = json.dumps(
                    tools, ensure_ascii=True, separators=(",", ":")
                )
            connector.updated_at = utcnow()
            session.add(connector)
            session.commit()
            session.refresh(connector)

        return ManagedConnectorValidationResult(
            success=error is None,
            connector_id=connector.id or 0,
            reachable=http_status is not None,
            valid=error is None,
            validation_status=connector.validation_status,
            http_status=http_status,
            discovery_url=discovery_url,
            tool_count=len(tools),
            warnings=warnings,
            error=error,
            validated_at=connector.last_validated_at or utcnow(),
        )

    @staticmethod
    async def call_mcp_tool(
        session: Session,
        user: User,
        connector_id: int,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        connector = ConnectorManagementService.get_connector(session, user, connector_id)
        if connector.transport != "streamable-http":
            raise HTTPException(
                status_code=400,
                detail="Tool execution requires a streamable-http MCP connector",
            )

        discovered_tools = ConnectorManagementService._extract_tools(
            _parse_json_field(connector.discovered_tools_json, [])
        )
        known_tool_names = {tool["name"] for tool in discovered_tools}
        if not known_tool_names:
            raise HTTPException(status_code=409, detail="Validate this connector before calling tools")
        if tool_name not in known_tool_names:
            raise HTTPException(status_code=404, detail="Tool was not discovered for this connector")

        endpoint = f"{connector.server_url.rstrip('/')}{connector.discovery_path or '/mcp'}"
        try:
            client = StreamableHTTPMCPClient(
                endpoint,
                connector.auth_type,
                decrypt_json(connector.auth_config_encrypted),
            )
            result = await client.call_tool(tool_name, arguments)
        except (MCPClientError, httpx.HTTPError) as exc:
            logger.warning(
                "MCP tool call failed for connector_id=%s tool=%s: %s",
                connector_id,
                tool_name,
                exc,
            )
            raise HTTPException(status_code=502, detail="MCP tool call failed") from exc

        return {
            "connector_id": connector.id or 0,
            "tool_name": tool_name,
            "result": result.result,
            "http_status": result.http_status,
        }
