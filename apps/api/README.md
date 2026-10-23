# ACME Salary API

FastAPI + SQLAlchemy 2.0 + SQLite. See [../../docs/architecture.md](../../docs/architecture.md).

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
alembic upgrade head
python -m app.seed              # 10,000 employees, demo users, exchange rates
uvicorn app.main:app --reload
```

OpenAPI docs: http://localhost:8000/docs

## Configuration

Environment variables, all prefixed `ACME_` (a `.env` file is also read):

| Variable | Default | Purpose |
|---|---|---|
| `ACME_DATABASE_URL` | `sqlite:///./acme.db` | SQLAlchemy URL |
| `ACME_JWT_SECRET` | `change-me-in-production` | HS256 signing key |
| `ACME_JWT_EXPIRY_HOURS` | `12` | Token lifetime |
| `ACME_CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed frontend origins (JSON list) |

## Tests

```bash
pytest
```

Tests use an in-memory SQLite database and a fixed clock. They do not touch the network or the filesystem.

## Layout

```
app/domain        pure business rules (money, salary history, validation, statistics)
app/models        SQLAlchemy tables
app/repositories  queries, scoped by organization
app/services      use cases
app/api           routers, schemas, auth dependencies
app/seed          deterministic data generator
alembic/          migrations
tests/
```
