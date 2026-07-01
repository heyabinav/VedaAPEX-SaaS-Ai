import os
from pathlib import Path

from app.core.api_key_config import KeyType
from app.services.key_manager import APIKeyManager


def test_key_manager_prefers_daily_then_monthly_then_permanent(monkeypatch, tmp_path):
    storage_path = tmp_path / "key_usage.json"
    monkeypatch.setenv("OPENAI_KEY_DAILY_1", "daily-key")
    monkeypatch.setenv("OPENAI_KEY_DAILY_1_LIMIT", "1")
    monkeypatch.setenv("OPENAI_KEY_MONTHLY_1", "monthly-key")
    monkeypatch.setenv("OPENAI_KEY_PERMANENT_1", "permanent-key")

    manager = APIKeyManager(storage_path=str(storage_path))

    assert manager.get_key("text", "openai") == "daily-key"
    manager.mark_used("daily-key", tokens_used=1)
    assert manager.get_key("text", "openai") == "monthly-key"
    manager.mark_used("monthly-key", tokens_used=1)
    assert manager.get_key("text", "openai") == "permanent-key"


def test_key_manager_marks_daily_keys_exhausted_when_limit_reached(monkeypatch, tmp_path):
    storage_path = tmp_path / "key_usage.json"
    monkeypatch.setenv("OPENAI_KEY_DAILY_1", "daily-key")
    monkeypatch.setenv("OPENAI_KEY_DAILY_1_LIMIT", "1")
    monkeypatch.setenv("OPENAI_KEY_MONTHLY_1", "monthly-key")

    manager = APIKeyManager(storage_path=str(storage_path))

    assert manager.get_key("text", "openai") == "daily-key"
    manager.mark_used("daily-key", tokens_used=1)

    key = next(k for k in manager._keys if k.key == "daily-key")
    assert key.is_exhausted is True
    assert manager.get_key("text", "openai") == "monthly-key"
