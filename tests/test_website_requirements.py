from pathlib import Path
import tempfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db.session import get_session
from app.models.user import User
from app.models.website_requirement import WebsiteRequirement
from app.routers.auth import get_current_user_auth
from app.routers.website import router as website_router


def _build_test_app():
    workspace_dir = Path(__file__).resolve().parents[1]
    temp_dir = tempfile.TemporaryDirectory(dir=str(workspace_dir))
    db_path = Path(temp_dir.name) / "website_requirements.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    app.include_router(website_router)
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user_auth] = override_get_current_user_auth
    return app, temp_dir, engine


def test_submit_website_requirements_without_save():
    app, temp_dir, engine = _build_test_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/website/requirements",
            json={
                "business_name": "Acme Co",
                "website_type": "Landing page",
                "target_audience": "Small business owners",
                "primary_objectives": ["Generate leads", "Showcase services"],
                "desired_features": ["Contact form", "Testimonials"],
                "content_pages": ["Home", "About", "Contact"],
                "preferred_style": "Modern and minimal",
                "budget": "Under $5,000",
                "launch_timeline": "Within 6 weeks",
                "additional_notes": "Integrate with email marketing.",
                "save": False,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["saved"] is False
        assert payload["questionnaire_id"] is None
        assert "Acme Co" in payload["summary"]

    engine.dispose()
    temp_dir.cleanup()


def test_submit_website_requirements_with_save():
    app, temp_dir, engine = _build_test_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/website/requirements",
            json={
                "business_name": "Hero Labs",
                "website_type": "E-commerce",
                "target_audience": "Tech buyers",
                "primary_objectives": ["Sell products", "Build trust"],
                "desired_features": ["Product catalog", "Checkout flow"],
                "content_pages": ["Home", "Shop", "Blog"],
                "preferred_style": "Bold and clean",
                "budget": "$10,000-$15,000",
                "launch_timeline": "Q3 launch",
                "additional_notes": "Mobile-first design.",
                "save": True,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["saved"] is True
        assert isinstance(payload["questionnaire_id"], int)
        assert "Hero Labs" in payload["summary"]

        with Session(engine) as session:
            entry = session.get(WebsiteRequirement, payload["questionnaire_id"])
            assert entry is not None
            assert entry.business_name == "Hero Labs"
            assert entry.user_id is not None

    engine.dispose()
    temp_dir.cleanup()
