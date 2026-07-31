import asyncio
import json

from app.services.providers.triposplat_provider import TripoSplatProvider


class DummyResponse:
    def __init__(self, status_code, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(payload or {})
        self.headers = headers or {"content-type": "application/json"}

    def json(self):
        return self._payload


class DummyClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return self.response


def test_generate_model_returns_url_from_gradio_payload(monkeypatch):
    expected_url = "https://example.com/model.glb"
    response = DummyResponse(200, {"data": [expected_url]})

    monkeypatch.setattr(
        "app.services.providers.triposplat_provider.httpx.AsyncClient",
        lambda *args, **kwargs: DummyClient(response),
    )
    monkeypatch.setattr(
        "app.services.providers.triposplat_provider.settings.TRIPOSPLAT_SPACE_URL",
        "https://vast-ai-triposplat.hf.space",
    )

    result = asyncio.run(TripoSplatProvider.generate_model("a red chair"))

    assert result == expected_url


def test_generate_model_uses_image_url_input(monkeypatch):
    expected_url = "https://example.com/model.glb"
    response = DummyResponse(200, {"data": [expected_url]})

    monkeypatch.setattr(
        "app.services.providers.triposplat_provider.httpx.AsyncClient",
        lambda *args, **kwargs: DummyClient(response),
    )
    monkeypatch.setattr(
        "app.services.providers.triposplat_provider.settings.TRIPOSPLAT_SPACE_URL",
        "https://vast-ai-triposplat.hf.space",
    )

    result = asyncio.run(
        TripoSplatProvider.generate_model(image_url="https://example.com/image.png")
    )

    assert result == expected_url
