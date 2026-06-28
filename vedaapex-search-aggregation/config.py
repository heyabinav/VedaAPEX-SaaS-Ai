"""Application configuration."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "VedaApex Search Aggregation"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"

    # API Keys
    PEXELS_API_KEY: str = ""
    NASA_API_KEY: str = "DEMO_KEY"
    WIKIMEDIA_API_KEY: str = ""

    # Provider Enablement
    ENABLE_PEXELS: bool = True
    ENABLE_WIKIMEDIA: bool = True
    ENABLE_NASA: bool = True

    # Cache
    CACHE_ENABLED: bool = True
    CACHE_TYPE: str = "memory"  # memory or redis
    CACHE_TTL: int = 3600
    REDIS_URL: str = "redis://localhost:6379/0"

    # Request
    REQUEST_TIMEOUT: int = 15
    MAX_RESULTS: int = 50
    DEFAULT_PAGE_SIZE: int = 20

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Query
    MIN_QUERY_LENGTH: int = 2
    MAX_QUERY_LENGTH: int = 200

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Query Keywords for Intelligent Routing
    SPACE_KEYWORDS: List[str] = [
        "nasa",
        "mars",
        "moon",
        "saturn",
        "jupiter",
        "galaxy",
        "astronaut",
        "rover",
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
        "apollo",
        "hubble",
        "mission",
        "launch",
        "shuttle",
        "iss",
        "esa",
        "roscosmos",
        "spacesuit",
        "gravity",
        "acceleration",
        "propulsion",
        "earth",
        "space travel",
        "zero gravity",
    ]

    SCIENTIFIC_KEYWORDS: List[str] = [
        "cancer",
        "cancer cell",
        "microscope",
        "biology",
        "neuron",
        "chemistry",
        "anatomy",
        "bacteria",
        "virus",
        "dna",
        "protein",
        "research",
        "medical",
        "science",
        "cell",
        "laboratory",
        "experiment",
        "physics",
        "medicine",
        "disease",
        "treatment",
        "vaccine",
        "molecule",
        "atom",
        "electron",
        "quantum",
        "genetics",
    ]

    GENERAL_KEYWORDS: List[str] = [
        "nature",
        "dog",
        "cat",
        "city",
        "business",
        "travel",
        "wallpaper",
        "people",
        "landscape",
        "water",
        "mountain",
        "beach",
        "forest",
        "animal",
        "bird",
        "flower",
        "building",
        "street",
        "sky",
        "sunset",
    ]

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = True

    def validate_config(self) -> None:
        """Validate configuration."""
        if not any([self.ENABLE_PEXELS, self.ENABLE_WIKIMEDIA, self.ENABLE_NASA]):
            raise ValueError("At least one provider must be enabled")

        if self.MAX_RESULTS < 1 or self.MAX_RESULTS > 100:
            raise ValueError("MAX_RESULTS must be between 1 and 100")

        if self.CACHE_TYPE not in ["memory", "redis"]:
            raise ValueError("CACHE_TYPE must be 'memory' or 'redis'")


config = Settings()
config.validate_config()
