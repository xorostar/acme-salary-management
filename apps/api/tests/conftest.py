"""Shared test fixtures.

Every test gets a fresh in-memory SQLite database with the schema created from
the models, a fixed clock (2025-06-15), and a TestClient bound to an app that
uses both. No test touches the network, the filesystem, or the real date.
"""

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.config import Settings
from app.db import Base, make_engine, make_session_factory
from app.main import create_app

FIXED_TODAY = date(2025, 6, 15)


def fixed_clock() -> date:
    return FIXED_TODAY


@pytest.fixture
def settings() -> Settings:
    return Settings(database_url="sqlite://", jwt_secret="test-secret", cors_origins=[])


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return make_session_factory(engine)


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as s:
        yield s


@pytest.fixture
def app(settings: Settings, engine: Engine):
    return create_app(settings=settings, engine=engine, clock=fixed_clock)


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
