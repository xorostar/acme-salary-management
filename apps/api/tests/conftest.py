"""Shared test fixtures.

Every test gets a fresh in-memory SQLite database with the schema created from
the models, a fixed clock (2025-06-15), and a TestClient bound to an app that
uses both. No test touches the network, the filesystem, or the real date.

Set ACME_TEST_DATABASE_URL to run the same suite against a real Postgres
(production runs on Postgres): tables are created before and dropped after
every test.
"""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.config import Settings
from app.db import Base, make_engine, make_session_factory
from app.main import create_app
from app.security import create_token
from tests.factories import make_admin, make_org, make_viewer

FIXED_TODAY = date(2025, 6, 15)


def fixed_clock() -> date:
    return FIXED_TODAY


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=os.environ.get("ACME_TEST_DATABASE_URL", "sqlite://"),
        jwt_secret="test-secret-that-is-at-least-32-bytes-long!",
        cors_origins=[],
    )


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    engine = make_engine(settings.database_url)
    Base.metadata.drop_all(engine)  # a previous run may have left tables behind
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
    if not engine.url.drivername.startswith("sqlite"):
        Base.metadata.drop_all(engine)


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


@dataclass(frozen=True)
class Seeded:
    org_id: int
    admin_id: int
    viewer_id: int


@pytest.fixture
def seeded(session_factory: sessionmaker[Session]) -> Seeded:
    """One organization with an admin and a viewer user, committed."""
    with session_factory() as s:
        org = make_org(s)
        admin = make_admin(s, org)
        viewer = make_viewer(s, org)
        s.commit()
        return Seeded(org_id=org.id, admin_id=admin.id, viewer_id=viewer.id)


def _headers(settings: Settings, user_id: int, org_id: int, role: str) -> dict[str, str]:
    token = create_token(
        secret=settings.jwt_secret,
        user_id=user_id,
        organization_id=org_id,
        role=role,
        expires_in=timedelta(hours=1),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(settings: Settings, seeded: Seeded) -> dict[str, str]:
    return _headers(settings, seeded.admin_id, seeded.org_id, "hr_admin")


@pytest.fixture
def viewer_headers(settings: Settings, seeded: Seeded) -> dict[str, str]:
    return _headers(settings, seeded.viewer_id, seeded.org_id, "hr_viewer")
