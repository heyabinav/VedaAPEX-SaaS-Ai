"""Small Streamable HTTP MCP client used by managed connectors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx


MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_CLIENT_INFO = {"name": "VedaApex Connector Registry", "version": "1.0.0"}


class MCPClientError(Exception):
    """A safe, user-facing MCP protocol failure."""


@dataclass
class MCPDiscovery:
    tools: list[dict[str, Any]]
    http_status: int


@dataclass
class MCPToolResult:
    result: Any
    http_status: int


class StreamableHTTPMCPClient:
    def __init__(self, endpoint: str, auth_type: str, auth_config: dict[str, Any]):
        self.endpoint = endpoint
        self.auth_type = auth_type
        self.auth_config = auth_config
        self.protocol_version = MCP_PROTOCOL_VERSION
        self.session_id: str | None = None

    async def discover_tools(self) -> MCPDiscovery:
        async with self._client() as client:
            await self._initialize(client)
            tools: list[dict[str, Any]] = []
            cursor: str | None = None
            last_status = 200
            for request_id in range(2, 22):
                params = {"cursor": cursor} if cursor else {}
                result, last_status = await self._request(client, request_id, "tools/list", params)
                page_tools = result.get("tools", []) if isinstance(result, dict) else []
                if not isinstance(page_tools, list):
                    raise MCPClientError("MCP tools/list returned an invalid tools payload")
                tools.extend(tool for tool in page_tools if isinstance(tool, dict) and tool.get("name"))
                cursor = result.get("nextCursor") if isinstance(result, dict) else None
                if not cursor:
                    return MCPDiscovery(tools=tools, http_status=last_status)
            raise MCPClientError("MCP tools/list exceeded the pagination limit")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        async with self._client() as client:
            await self._initialize(client)
            result, status = await self._request(
                client,
                2,
                "tools/call",
                {"name": tool_name, "arguments": arguments},
            )
            return MCPToolResult(result=result, http_status=status)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=False,
            headers=self._headers(),
        )

    def _headers(self, include_protocol_version: bool = False) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": "VedaApex-MCP-Registry/1.0",
        }
        if include_protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        if self.session_id:
            headers["MCP-Session-Id"] = self.session_id

        if self.auth_type == "api_key":
            header_name = self.auth_config.get("api_key_header")
            secret = self.auth_config.get("api_key")
            prefix = self.auth_config.get("api_key_prefix", "")
            if not header_name or not secret:
                raise MCPClientError("API key connector is missing its stored credential")
            headers[str(header_name)] = f"{prefix}{secret}"
        elif self.auth_type in {"bearer", "oauth2"}:
            secret = self.auth_config.get("access_token")
            if not secret:
                raise MCPClientError("Token connector is missing its stored access token")
            header_name = self.auth_config.get("header_name", "Authorization")
            scheme = self.auth_config.get("scheme", "Bearer")
            headers[str(header_name)] = f"{scheme} {secret}".strip()

        return headers

    async def _initialize(self, client: httpx.AsyncClient) -> None:
        result, response = await self._request(
            client,
            1,
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": MCP_CLIENT_INFO,
            },
            include_protocol_version=False,
        )
        if not isinstance(result, dict) or not result.get("protocolVersion"):
            raise MCPClientError("MCP server returned an invalid initialize response")
        self.protocol_version = str(result["protocolVersion"])
        self.session_id = response.headers.get("MCP-Session-Id")

        notification = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        response = await client.post(self.endpoint, json=notification, headers=self._headers(True))
        if response.status_code >= 400:
            raise MCPClientError(f"MCP initialization notification failed with HTTP {response.status_code}")

    async def _request(
        self,
        client: httpx.AsyncClient,
        request_id: int,
        method: str,
        params: dict[str, Any],
        include_protocol_version: bool = True,
    ) -> tuple[Any, httpx.Response]:
        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        response = await client.post(
            self.endpoint,
            json=message,
            headers=self._headers(include_protocol_version),
        )
        if response.status_code >= 400:
            raise MCPClientError(f"MCP {method} failed with HTTP {response.status_code}")
        payload = self._response_payload(response)
        if not isinstance(payload, dict):
            raise MCPClientError(f"MCP {method} returned an invalid JSON-RPC response")
        if payload.get("error"):
            detail = payload["error"].get("message", "unknown JSON-RPC error") if isinstance(payload["error"], dict) else "unknown JSON-RPC error"
            raise MCPClientError(f"MCP {method} failed: {detail}")
        if "result" not in payload:
            raise MCPClientError(f"MCP {method} response did not contain a result")
        return payload["result"], response

    @staticmethod
    def _response_payload(response: httpx.Response) -> Any:
        content_type = response.headers.get("content-type", "").lower()
        if "text/event-stream" in content_type:
            data_lines: list[str] = []
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    data_lines.append(line[5:].strip())
            for item in data_lines:
                try:
                    payload = json.loads(item)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict) and ("result" in payload or "error" in payload):
                    return payload
            raise MCPClientError("MCP SSE response did not contain a JSON-RPC result")
        try:
            return response.json()
        except ValueError as exc:
            raise MCPClientError("MCP server returned invalid JSON") from exc

