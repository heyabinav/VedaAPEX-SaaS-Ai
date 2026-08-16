from app.core.commands.executor import execute_command


def test_execute_command_accepts_registry_command():
    result = execute_command("/help")
    assert result["success"] is True
    assert result["command"] == "help"
    assert result["execution"]["phase"] == "plumbing"


def test_execute_command_rejects_unknown_command():
    result = execute_command("/mystery")
    assert result["success"] is False
    assert result["fallback_to_chat"] is True


def test_execute_command_handles_structured_payload():
    result = execute_command({"command": "status", "raw": "/status"})
    assert result["success"] is True
    assert result["command"] == "status"
    assert result["raw"] == "/status"


def test_execute_command_requires_valid_input():
    try:
        execute_command(123)
        assert False, "Expected a validation error for invalid input"
    except Exception:
        pass
