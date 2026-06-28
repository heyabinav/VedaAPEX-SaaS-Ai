"""
Configuration module for VedaApex Video Search Backend.
Centralized configuration management using pydantic.
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration settings."""

    # ========================================================================
    # APPLICATION SETTINGS
    # ========================================================================
    APP_NAME: str = "VedaApex Video Search Backend"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ========================================================================
    # PEXELS API SETTINGS
    # ========================================================================
    PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")
    PEXELS_API_URL: str = os.getenv("PEXELS_API_URL", "https://api.pexels.com")
    PEXELS_SEARCH_ENDPOINT: str = "/v1/search"
    PEXELS_VIDEOS_ENDPOINT: str = "/videos/search"

    # ========================================================================
    # CACHE SETTINGS
    # ========================================================================
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TYPE: str = os.getenv("CACHE_TYPE", "memory")  # "memory" or "redis"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ========================================================================
    # RATE LIMITING SETTINGS
    # ========================================================================
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # ========================================================================
    # REQUEST SETTINGS
    # ========================================================================
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "80"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "80"))
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))

    # ========================================================================
    # CORS SETTINGS
    # ========================================================================
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # ========================================================================
    # SECURITY SETTINGS
    # ========================================================================
    ALLOWED_API_KEYS: List[str] = os.getenv("ALLOWED_API_KEYS", "").split(",")
    ENABLE_API_KEY_AUTH: bool = os.getenv("ENABLE_API_KEY_AUTH", "true").lower() == "true"

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.APP_ENV.lower() == "production"

    def validate_config(self) -> None:
        """Validate configuration."""
        if not self.PEXELS_API_KEY:
            raise ValueError("PEXELS_API_KEY environment variable is required")

        if self.CACHE_TYPE not in ["memory", "redis"]:
            raise ValueError("CACHE_TYPE must be 'memory' or 'redis'")

        if self.CACHE_TTL < 60:
            raise ValueError("CACHE_TTL must be at least 60 seconds")

        if self.REQUEST_TIMEOUT < 5:
            raise ValueError("REQUEST_TIMEOUT must be at least 5 seconds")

        if self.MAX_RESULTS < 1 or self.MAX_RESULTS > 80:
            raise ValueError("MAX_RESULTS must be between 1 and 80")

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.validate_config()
    return settings


# Global settings instance
config = get_settings()
