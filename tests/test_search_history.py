from pathlib import Path
import tempfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.routers.search_history import router as search_history_router


def _build_test_app():
    workspace_dir = Path(__file__).resolve().parents[1]
    temp_dir = tempfile.TemporaryDirectory(dir=str(workspace_dir))
    db_path = Path(temp_dir.name) / "search_history.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(email="tester@example.com", hashed_password="secret")
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    def override_get_session():
        with Session(engine) as session:
            yield session

    def override_get_current_user_auth():
        with Session(engine) as session:
            return session.get(User, user_id)

    app = FastAPI()
    app.include_router(search_history_router, prefix="/api/v1")
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user_auth] = override_get_current_user_auth
    return app, temp_dir, engine


def test_search_history_save_list_and_results():
    app, temp_dir, engine = _build_test_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/search/history",
            json={
                "title": "Morning inspiration",
                "query": "mountain sunrise",
                "source": "web",
                "notes": "saved from homepage search",
                "results": [
                    {"title": "Sunrise Over Mountains", "url": "https://example.com/1"},
                    {"title": "Golden Hour Peaks", "url": "https://example.com/2"},
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["title"] == "Morning inspiration"
        assert payload["data"]["result_count"] == 2

        list_response = client.get("/api/v1/search/history")
        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert list_payload["pagination"]["total"] == 1
        assert list_payload["data"][0]["result_count"] == 2

        results_response = client.get("/api/v1/search/history/1/results")
        assert results_response.status_code == 200
        results_payload = results_response.json()
        assert results_payload["result_count"] == 2
        assert len(results_payload["results"]) == 2

    engine.dispose()
    temp_dir.cleanup()


def test_generate_search_title_from_query_and_results():
    app, temp_dir, engine = _build_test_app()

    with TestClient(app) as client:
        query_response = client.post(
            "/api/v1/search/title/generate",
            json={
                "query": "best budget travel camera 2026",
                "source": "web",
            },
        )
        assert query_response.status_code == 200
        query_payload = query_response.json()
        assert query_payload["title"] == "Budget Travel Camera 2026"

        result_response = client.post(
            "/api/v1/search/title/generate",
            json={
                "query": "something generic",
                "results": [{"title": "NASA Mars Rover Images"}],
            },
        )
        assert result_response.status_code == 200
        result_payload = result_response.json()
        assert result_payload["title"] == "NASA Mars Rover Images"

    engine.dispose()
    temp_dir.cleanup()
