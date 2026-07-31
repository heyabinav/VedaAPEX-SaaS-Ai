import os
from datetime import datetime, timedelta

os.environ.setdefault("OAUTH_TOKEN_ENCRYPTION_KEY", "test-secret-key-1234567890abcdef")

from sqlmodel import SQLModel, Session, create_engine

from app.helpers.token_helper import get_user_token, is_token_valid, save_user_token
from app.models import token as token_models  # noqa: F401
from app.models import user as user_model  # noqa: F401
from app.models.user_oauth_tokens import UserOAuthToken


def test_save_and_retrieve_encrypted_oauth_token(tmp_path):
    db_path = tmp_path / "oauth_test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        save_user_token(
            42,
            "figma",
            "access-secret",
            "refresh-secret",
            datetime.utcnow() + timedelta(hours=1),
            session=session,
        )

        stored = get_user_token(42, "figma", session=session)
        assert stored is not None
        assert stored["access_token"] == "access-secret"
        assert stored["refresh_token"] == "refresh-secret"
        assert is_token_valid(42, "figma", session=session)
        assert session.get(UserOAuthToken, stored["id"]).platform == "figma"
