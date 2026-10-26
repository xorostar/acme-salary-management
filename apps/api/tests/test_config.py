import pytest
from pydantic import ValidationError

from app.config import Settings


def test_development_allows_default_secret():
    assert Settings(environment="development").jwt_secret == "change-me-in-production"


def test_production_refuses_default_secret():
    with pytest.raises(ValidationError, match="ACME_JWT_SECRET"):
        Settings(environment="production")


def test_production_refuses_short_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="short")


def test_production_accepts_long_secret():
    s = Settings(environment="production", jwt_secret="x" * 32)
    assert s.environment == "production"
