import asyncio

from app.services.providers.trellis2_provider import Trellis2Provider


class DummyResponse:
    def __init__(self, payload=None, status_code=200, text=""):
        self._payload = payload or {}
        self.status_code = status_code
        self.text = text or ""
        self.headers = {"content-type": "application/json"}

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


def test_generate_model_returns_url_from_payload(monkeypatch):
    expected_url = "https://example.com/model.glb"
    response = DummyResponse({"data": [expected_url]})

    monkeypatch.setattr(
        "app.services.providers.trellis2_provider.httpx.AsyncClient",
        lambda *args, **kwargs: DummyClient(response),
    )
    monkeypatch.setattr(
        "app.services.providers.trellis2_provider.settings.TRELLIS2_SPACE_URL",
        "https://microsoft-trellis2.hf.space",
    )

    result = asyncio.run(Trellis2Provider.generate_model("a red chair"))

    assert result == expected_url
