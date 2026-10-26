"""Database engine, session factory, and declarative base.

SQLite needs two pragmas that are off by default: foreign keys and WAL mode.
Both are set per connection so they apply to in-memory test databases too.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def _enable_sqlite_pragmas(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def make_engine(database_url: str) -> Engine:
    """Create an engine.

    - In-memory SQLite uses a single shared connection so every session in a
      test sees the same schema and data.
    - Postgres (production on Vercel + Neon) uses a small pool with pre-ping, so
      a connection dropped while a serverless instance was idle is replaced
      transparently. Prepared statements are disabled because Neon's pooled
      endpoint (PgBouncer, transaction mode) does not support them.
    """
    kwargs: dict = {}
    if database_url.startswith("postgresql"):
        kwargs.update(
            pool_size=2,
            max_overflow=3,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={"prepare_threshold": None},
        )
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url or database_url.endswith("sqlite://"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(database_url, **kwargs)
    if database_url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_pragmas)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """FastAPI dependency body: yield a session, roll back on error."""
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
