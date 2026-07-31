from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_mcp_routes_are_registered():
    paths = {
        getattr(route, "path", None)
        for route in app.routes
        if getattr(route, "path", None)
    }
    assert "/mcp" in paths
    assert "/sse" in paths


def test_mcp_server_exposes_expected_tools():
    tool_names = set(getattr(app.state, "mcp_tool_names", []))
    assert {"health_check", "unified_search", "browser_search", "chat"}.issubset(tool_names)


def test_existing_health_endpoint_still_works():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
