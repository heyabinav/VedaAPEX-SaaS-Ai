"""Automated unit test suite for Payment System & Razorpay Integration."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db.session import get_session
from app.main import app
from app.models.token import SubscriptionPlan
from app.models.user import User
from app.routers.auth import get_current_user_auth


@pytest.fixture(name="db_session")
def db_session_fixture():
    import app.models.user  # noqa: F401
    import app.models.token  # noqa: F401

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Add sample subscription plan
        plan = SubscriptionPlan(
            slug="pro-monthly",
            name="Pro Plan",
            price="499.00",
            billing_cycle="monthly",
            token_allocation=5000,
            is_active=True,
        )
        session.add(plan)
        session.commit()
        yield session


@pytest.fixture
def client_override_auth(db_session: Session):
    test_user = User(
        id=888,
        email="payment_user@example.com",
        full_name="Payment Test User",
        referral_code="ref_payment_888",
        is_active=True,
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    def _override_auth():
        return test_user

    def _override_get_session():
        yield db_session

    app.dependency_overrides[get_current_user_auth] = _override_auth
    app.dependency_overrides[get_session] = _override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_payment_config_endpoint(client_override_auth):
    response = client_override_auth.get("/api/v1/payments/config")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["key_id"] == "rzp_live_T3WW3Rw0QCj8yB"
    assert data["currency"] == "INR"


def test_create_payment_order(client_override_auth):
    mock_order_data = {
        "id": "order_test_123456",
        "entity": "order",
        "amount": 49900,
        "currency": "INR",
        "status": "created",
    }

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: mock_order_data

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        response = client_override_auth.post(
            "/api/v1/payments/orders",
            json={"plan_slug": "pro-monthly"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["keyId"] == "rzp_live_T3WW3Rw0QCj8yB"
        assert data["data"]["order"]["order_id"] == "order_test_123456"
        assert data["data"]["order"]["amount_paise"] == 49900


def test_payment_history_endpoint(client_override_auth):
    response = client_override_auth.get("/api/v1/payments/history")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
