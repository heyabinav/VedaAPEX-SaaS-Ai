from sqlalchemy.exc import OperationalError

import app.db.session as session_module


class DummyEngine:
    def __init__(self, url: str):
        self.url = url


def test_init_db_falls_back_to_sqlite_when_create_all_fails(monkeypatch):
    created_urls = []

    def fake_create_engine(url, **kwargs):
        created_urls.append(url)
        return DummyEngine(url)

    def fake_create_all(engine):
        if getattr(engine, "url", None) == "postgresql://example":
            raise OperationalError("boom", None, Exception("boom"))

    monkeypatch.setattr(session_module, "engine", DummyEngine("postgresql://example"))
    monkeypatch.setattr(session_module, "create_engine", fake_create_engine)
    monkeypatch.setattr(session_module.SQLModel.metadata, "create_all", fake_create_all)
    monkeypatch.setattr(session_module, "_ensure_missing_schema_columns", lambda: None)
    monkeypatch.setattr(session_module, "_database_url", "postgresql://example")
    monkeypatch.setattr(session_module, "_is_sqlite", False)

    session_module.init_db()

    assert created_urls[-1].startswith("sqlite:///")
    assert session_module._database_url.startswith("sqlite")
