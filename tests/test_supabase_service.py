import pytest

from app.services import supabase_service
from app.services.supabase_service import SupabaseService


def test_supabase_headers_prefer_public_key(monkeypatch):
    class DummySettings:
        SUPABASE_KEY = "anon-key"
        SUPABASE_SERVICE_ROLE_KEY = "service-key"

    monkeypatch.setattr(supabase_service, "settings", DummySettings())

    headers = SupabaseService._headers(access_token="token123")
    assert headers["apikey"] == "anon-key"
    assert headers["Authorization"] == "Bearer token123"
