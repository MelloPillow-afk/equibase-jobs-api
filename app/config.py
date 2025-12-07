"""Application configuration using Pydantic settings."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Base configuration shared across all environments."""

    SUPABASE_URL: str = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


class DevelopmentSettings(BaseConfig):
    """Development environment settings."""

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Application Configuration
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"

    # CORS Configuration
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Server Configuration
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000


class ProductionSettings(BaseConfig):
    """Production environment settings."""

    # Celery Configuration (must be set via env vars in production)
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Application Configuration
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"

    # CORS Configuration (must be set via env vars in production)
    CORS_ORIGINS: list[str] = ["https://equibase-pdf-processor-268lkuw66-mellopillow-afks-projects.vercel.app"]

    # Server Configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = int(os.environ.get("PORT", "8000"))

    def __init__(self, **kwargs):
        # Get Celery URLs from environment
        kwargs["CELERY_BROKER_URL"] = os.environ.get("CELERY_BROKER_URL", "")
        kwargs["CELERY_RESULT_BACKEND"] = os.environ.get("CELERY_RESULT_BACKEND", "")

        super().__init__(**kwargs)


def get_settings() -> BaseConfig:
    """Get settings based on ENVIRONMENT env variable."""
    env = os.environ.get("ENVIRONMENT", "development").lower()

    if env == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()


settings = get_settings()
