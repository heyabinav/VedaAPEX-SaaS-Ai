from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import oauth as oauth_module


class FakeAuthClient:
    class Auth:
        def sign_in_with_oauth(self, payload):
            return {"url": "https://accounts.google.com/o/oauth2/v2/auth?test=1"}

    auth = Auth()


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
