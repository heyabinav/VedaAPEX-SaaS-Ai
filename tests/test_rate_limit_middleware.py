from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.rate_limit import RateLimitMiddleware


def test_rate_limit_middleware_blocks_after_limit():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    client = TestClient(app)

    first = client.get("/ping")
    second = client.get("/ping")
    third = client.get("/ping")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429

    body = third.json()
    assert body["success"] is False
    assert body["error"] == "RateLimitError"
    assert body["status_code"] == 429
    assert body["details"]["limit"] == 2
