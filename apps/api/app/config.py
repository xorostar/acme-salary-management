"""Application settings loaded from environment variables (or a .env file)."""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-in-production"
MIN_SECRET_BYTES = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ACME_", env_file=".env", extra="ignore")

    environment: Literal["development", "production"] = "development"
    database_url: str = "sqlite:///./acme.db"
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_expiry_hours: int = 12
    cors_origins: list[str] = ["http://localhost:3000"]

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        """Fail at startup rather than sign salary-data tokens with a known key."""
        if self.environment == "production" and (
            self.jwt_secret == DEFAULT_JWT_SECRET
            or len(self.jwt_secret.encode()) < MIN_SECRET_BYTES
        ):
            raise ValueError(
                f"ACME_JWT_SECRET must be set to at least {MIN_SECRET_BYTES} bytes in production"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
