from utils.time import utcnow

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import oauth as oauth_module


class FakeAuthClient:
    class Auth:
        def sign_in_with_oauth(self, payload):
            return {"url": "https://accounts.google.com/o/oauth2/v2/auth?test=1"}

    auth = Auth()


class FakeUser:
    id = 1
    canva_refresh_token = "refresh-token-123"


def _build_client(monkeypatch):
    monkeypatch.setattr(oauth_module, "_get_supabase_client", lambda: FakeAuthClient())
    app = FastAPI()
    app.include_router(oauth_module.router)
    return TestClient(app)


def test_google_login_returns_json_for_api_requests(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get("/auth/google/login", headers={"accept": "application/json"})

    assert response.status_code == 200
    assert response.json()["provider"] == "google"
    assert response.json()["auth_url"] == "https://accounts.google.com/o/oauth2/v2/auth?test=1"


def test_google_login_redirects_for_browser_navigation(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get(
        "/auth/google/login",
        headers={"accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://accounts.google.com/o/oauth2/v2/auth?test=1"


def test_canva_login_returns_json_for_api_requests(monkeypatch):
    async def fake_authenticated_user(request, session):
        return FakeUser()

    monkeypatch.setattr(oauth_module, "_get_authenticated_local_user", fake_authenticated_user)
    monkeypatch.setattr(oauth_module, "get_session", lambda: None)
    monkeypatch.setattr(oauth_module.CanvaOAuthService, "build_authorization_url", lambda state: "https://accounts.canva.com/oauth/authorize?test=1")

    client = _build_client(monkeypatch)
    response = client.get("/auth/canva/login", headers={"accept": "application/json"})

    assert response.status_code == 200
    assert response.json()["provider"] == "canva"
    assert response.json()["auth_url"] == "https://accounts.canva.com/oauth/authorize?test=1"


def test_canva_callback_redirects_on_missing_code(monkeypatch):
    client = _build_client(monkeypatch)
    response = client.get("/auth/canva/callback", follow_redirects=False)

    assert response.status_code == 302
    assert "error=missing_code" in response.headers["location"]


def test_canva_refresh_returns_updated_tokens(monkeypatch):
    async def fake_authenticated_user(request, session):
        return FakeUser()

    async def fake_refresh_token(refresh_token):
        return {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_at": utcnow() + timedelta(hours=1),
        }

    async def fake_save_canva_tokens_for_user(user, token_data, session):
        return None

    monkeypatch.setattr(oauth_module, "_get_authenticated_local_user", fake_authenticated_user)
    monkeypatch.setattr(oauth_module, "_save_canva_tokens_for_user", fake_save_canva_tokens_for_user)
    monkeypatch.setattr(oauth_module.CanvaOAuthService, "refresh_token", fake_refresh_token)

    client = _build_client(monkeypatch)
    response = client.post("/auth/canva/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["canva_connected"] is True
    assert data["expires_at"] is not None