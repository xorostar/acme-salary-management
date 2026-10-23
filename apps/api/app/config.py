"""Application settings loaded from environment variables (or a .env file)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ACME_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./acme.db"
    jwt_secret: str = "change-me-in-production"
    jwt_expiry_hours: int = 12
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
