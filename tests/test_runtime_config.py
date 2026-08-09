from app.core.config import Settings


def test_runtime_port_and_origins_are_resolved_from_env(monkeypatch):
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com,https://admin.example.com")

    settings = Settings()

    assert settings.get_runtime_port() == 9000
    assert settings.get_allowed_origins() == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_runtime_validation_warns_in_development_without_raising(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    settings = Settings()
    warnings = settings.validate_runtime_environment()

    assert warnings
    assert any("SECRET_KEY" in warning for warning in warnings)


def test_deployment_alias_env_vars_are_resolved(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("JWT_ACCESS_SECRET", "deploy-secret")
    monkeypatch.setenv("NODE_ENV", "production")
    monkeypatch.setenv("R2_BUCKET", "media-bucket")
    monkeypatch.setenv("R2_ENDPOINT", "https://r2.example.com")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    settings = Settings()

    assert settings.SECRET_KEY == "deploy-secret"
    assert settings.APP_ENV == "production"
    assert settings.R2_BUCKET_NAME == "media-bucket"
    assert settings.R2_ENDPOINT_URL == "https://r2.example.com"
    assert settings.SUPABASE_KEY == "anon-key"
