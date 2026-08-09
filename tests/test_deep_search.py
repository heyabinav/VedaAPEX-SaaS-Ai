"""Unit tests for Deep Search feature."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db.session import get_session
from app.main import app
from app.models.user import User
from app.routers.auth import get_current_user_auth


@pytest.fixture(name="db_session")
def db_session_fixture():
    import app.models.user  # noqa: F401
    import app.models.token  # noqa: F401
    import app.models.search_history  # noqa: F401
    import app.models.search_history_result  # noqa: F401

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def client_override_auth(db_session: Session):
    test_user = User(
        email="deepsearch_user@example.com",
        full_name="Deep Search Test User",
        referral_code="ref_deepsearch_999",
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


def test_deep_search_endpoint(client_override_auth):
    mock_result = {
        "query": "Quantum Computing breakthroughs 2026",
        "subqueries": [
            "Quantum hardware milestones 2026",
            "Commercial quantum computing deployment",
            "Quantum error correction benchmarks",
        ],
        "report": "# Deep Search Report\n\nQuantum computing has achieved commercial fault tolerance.",
        "sources": [
            {
                "title": "Quantum Breakthroughs 2026",
                "url": "https://example.com/quantum",
                "content": "Fault tolerant quantum processing units announced.",
                "score": 0.95,
            }
        ],
        "total_sources_found": 1,
    }

    with patch("app.services.deep_search_service.DeepSearchService.deep_search", new_callable=AsyncMock) as mock_ds:
        mock_ds.return_value = mock_result

        response = client_override_auth.post(
            "/api/v1/search/deep",
            json={"query": "Quantum Computing breakthroughs 2026", "depth": "deep", "save_history": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["query"] == "Quantum Computing breakthroughs 2026"
        assert len(data["subqueries"]) == 3
        assert "Deep Search Report" in data["report"]
        assert len(data["sources"]) == 1
        assert data["history_id"] is not None
