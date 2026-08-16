from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.commands.parser import parse_command
from app.routers.auth import get_current_user_auth
from app.routers.commands import router as commands_router


def test_parse_command_root_falls_back_to_chat():
    assert parse_command("/") is None


def test_parse_command_skills():
    assert parse_command("/skills") == {"command": "skills"}


def test_parse_command_agents_research():
    assert parse_command("/agents research latest models") == {
        "command": "agents",
        "subcommand": "research",
        "arguments": "latest models",
    }


def test_parse_command_images():
    assert parse_command("/images cats") == {"command": "images", "arguments": "cats"}


def test_parse_command_unknown_returns_structured_fallback():
    result = parse_command("/unknowncmd hello")
    assert result["command"] == "unknown"
    assert result["fallback_to_chat"] is True
    assert result["raw"] == "/unknowncmd hello"


def test_parse_command_does_not_trigger_on_double_leading_slash_or_mid_sentence():
    assert parse_command("//skills") is None
    assert parse_command("hello /skills there") is None


def test_commands_endpoint_returns_only_enabled_entries():
    app = FastAPI()
    app.include_router(commands_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user_auth] = lambda: SimpleNamespace(id=123)

    client = TestClient(app)
    response = client.get("/api/v1/commands")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["commands"], list)
    assert all(item["enabled"] is True for item in payload["commands"])
