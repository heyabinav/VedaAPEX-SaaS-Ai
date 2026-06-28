"""
Configuration module for VedaApex Space Image backend.
Centralized settings management with multi-provider support.
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "VedaApex Space Image"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # NASA API
    NASA_API_URL: str = os.getenv("NASA_API_URL", "https://images-api.nasa.gov/search")
    NASA_DEMO_KEY: str = os.getenv("NASA_DEMO_KEY", "DEMO_KEY")

    # Providers
    ENABLED_PROVIDERS: str = os.getenv("ENABLED_PROVIDERS", "nasa,wikimedia,pexels")
    DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "nasa")

    # Provider priorities
    SPACE_QUERY_PRIORITY: str = os.getenv("SPACE_QUERY_PRIORITY", "nasa,wikimedia,pexels")
    SCIENTIFIC_QUERY_PRIORITY: str = os.getenv("SCIENTIFIC_QUERY_PRIORITY", "wikimedia,nasa,pexels")
    GENERAL_QUERY_PRIORITY: str = os.getenv("GENERAL_QUERY_PRIORITY", "pexels,wikimedia,nasa")

    # Cache
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TYPE: str = os.getenv("CACHE_TYPE", "memory")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Request
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "50"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Search
    MIN_QUERY_LENGTH: int = int(os.getenv("MIN_QUERY_LENGTH", "2"))
    MAX_QUERY_LENGTH: int = int(os.getenv("MAX_QUERY_LENGTH", "200"))
    DEDUPLICATION_ENABLED: bool = os.getenv("DEDUPLICATION_ENABLED", "true").lower() == "true"
    RANKING_ENABLED: bool = os.getenv("RANKING_ENABLED", "true").lower() == "true"

    # Query categorization keywords
    SPACE_KEYWORDS: List[str] = [
        "nasa",
        "mars",
        "moon",
        "astronaut",
        "galaxy",
        "rover",
        "earth",
        "saturn",
        "jupiter",
        "space",
        "spacecraft",
        "satellite",
        "orbit",
        "cosmic",
        "star",
        "solar",
        "sun",
        "planet",
        "asteroid",
        "comet",
        "nebula",
    ]

    SCIENTIFIC_KEYWORDS: List[str] = [
        "cancer cell",
        "neuron",
        "microscope",
        "biology",
        "science",
        "research",
        "medical",
        "anatomy",
        "cell",
        "bacteria",
        "virus",
        "dna",
        "protein",
        "chemistry",
        "physics",
        "experiment",
        "laboratory",
    ]

    def is_production(self) -> bool:
        """Check if production."""
        return self.APP_ENV.lower() == "production"

    def validate_config(self) -> None:
        """Validate configuration."""
        if self.CACHE_TYPE not in ["memory", "redis"]:
            raise ValueError("CACHE_TYPE must be 'memory' or 'redis'")

        if self.CACHE_TTL < 60:
            raise ValueError("CACHE_TTL must be at least 60 seconds")

        if self.REQUEST_TIMEOUT < 5:
            raise ValueError("REQUEST_TIMEOUT must be at least 5 seconds")

        if self.MAX_RESULTS < 1 or self.MAX_RESULTS > 100:
            raise ValueError("MAX_RESULTS must be between 1 and 100")

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings."""
    settings = Settings()
    settings.validate_config()
    return settings


config = get_settings()
