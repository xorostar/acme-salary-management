"""FastAPI application factory.

create_app() takes its dependencies explicitly so tests can pass an in-memory
engine and a fixed clock instead of patching globals.
"""

from collections.abc import Callable
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from app.api.errors import register_error_handlers
from app.api.routers import analytics, auth, employee_csv, employees, payroll, reference
from app.config import Settings, get_settings
from app.db import make_engine, make_session_factory

Clock = Callable[[], date]


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    engine = engine or make_engine(settings.database_url)
    clock = clock or date.today

    app = FastAPI(title="ACME Salary API", version="0.1.0")
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.clock = clock

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(employee_csv.router)  # before employees: /export.csv vs /{id}
    app.include_router(employees.router)
    app.include_router(reference.router)
    app.include_router(analytics.router)
    app.include_router(payroll.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
