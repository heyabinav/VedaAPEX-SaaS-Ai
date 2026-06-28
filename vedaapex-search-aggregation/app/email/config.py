"""Configuration for email verification module."""

import os
from typing import Optional
from datetime import timedelta


class EmailConfig:
    """Email service configuration."""

    # Brevo SMTP Settings
    BREVO_SMTP_HOST: str = os.getenv("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
    BREVO_SMTP_PORT: int = int(os.getenv("BREVO_SMTP_PORT", "587"))
    BREVO_SMTP_USERNAME: str = os.getenv("BREVO_SMTP_USERNAME", "")
    BREVO_SMTP_PASSWORD: str = os.getenv("BREVO_SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@vedaapex.com")

    # Application Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./email_verification.db")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8000")
    APP_ENV: str = os.getenv("APP_ENV", "development")

    # Token Settings
    VERIFICATION_TOKEN_EXPIRY: timedelta = timedelta(hours=24)
    VERIFICATION_TOKEN_LENGTH: int = 32

    # Security Settings
    PASSWORD_MIN_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_ATTEMPT_TIMEOUT: timedelta = timedelta(minutes=15)

    # Email Settings
    VERIFICATION_EMAIL_SUBJECT: str = "Verify Your Email - VedaAPEX"
    RESEND_EMAIL_COOLDOWN: timedelta = timedelta(minutes=5)

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production."""
        return cls.APP_ENV == "production"

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        required = [
            cls.BREVO_SMTP_USERNAME,
            cls.BREVO_SMTP_PASSWORD,
            cls.EMAIL_FROM,
            cls.SECRET_KEY,
        ]
        return all(required)
