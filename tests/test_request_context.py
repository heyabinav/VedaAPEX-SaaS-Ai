"""
Tests for the request context middleware.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.request_context import RequestContextMiddleware


@pytest.fixture
def app():
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    @app.get("/slow")
    async def slow_endpoint():
        import asyncio
        await asyncio.sleep(0.1)
        return {"ok": True}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestRequestContextMiddleware:
    def test_request_id_added(self, client):
        response = client.get("/test")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 12

    def test_process_time_added(self, client):
        response = client.get("/test")
        assert "X-Process-Time" in response.headers
        process_time = int(response.headers["X-Process-Time"])
        assert process_time >= 0

    def test_process_time_positive_for_slow(self, client):
        response = client.get("/slow")
        process_time = int(response.headers["X-Process-Time"])
        assert process_time >= 50  # At least 50ms due to 100ms sleep

    def test_request_id_unique_per_request(self, client):
        r1 = client.get("/test")
        r2 = client.get("/test")
        assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]
