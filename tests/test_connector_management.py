from app.schemas.connector_management import ManagedConnectorCreate, ManagedConnectorUpdate
from app.services.connector_management_service import ConnectorManagementService


def test_managed_connector_create_normalizes_url_and_path():
    body = ManagedConnectorCreate(
        name="Acme MCP",
        server_url="https://example.com/",
        discovery_path="mcp",
        auth_type="api_key",
        auth_config={"api_key_header": "X-API-Key", "api_key": "secret"},
    )

    assert body.server_url == "https://example.com"
    assert body.discovery_path == "/mcp"


def test_managed_connector_update_rejects_bad_url():
    try:
        ManagedConnectorUpdate(server_url="not-a-url")
    except Exception as exc:
        assert "server_url" in str(exc)
    else:
        raise AssertionError("Expected validation failure for bad server_url")


def test_auth_scaffold_templates_cover_common_auth_modes():
    oauth2 = ConnectorManagementService.build_auth_scaffold("oauth2")
    api_key = ConnectorManagementService.build_auth_scaffold("api_key")

    assert oauth2.auth_type == "oauth2"
    assert "client_id" in oauth2.required_fields
    assert api_key.auth_type == "api_key"
    assert "api_key" in api_key.secrets_to_store


def test_extract_tools_understands_standard_mcp_payload():
    tools = ConnectorManagementService._extract_tools(
        {
            "tools": [
                {
                    "name": "createTask",
                    "description": "Create a task",
                    "inputSchema": {"type": "object"},
                }
            ]
        }
    )

    assert len(tools) == 1
    assert tools[0]["name"] == "createTask"
    assert tools[0]["input_schema"] == {"type": "object"}
