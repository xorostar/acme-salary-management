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

Demo logins: `admin@acme.example` (hr_admin) and `viewer@acme.example` (hr_viewer), password
`acme-demo-2026` (override with `ACME_DEMO_PASSWORD` before seeding).

### Seed options

| Command | Effect |
|---|---|
| `python -m app.seed` | Seed an empty database; refuses if data exists |
| `python -m app.seed --reset` | Delete all rows, then seed |
| `python -m app.seed --if-empty` | Seed only when empty, otherwise exit 0 (used on container boot) |
| `python -m app.seed --count 500 --seed 7` | Smaller or different deterministic data |

The generator is deterministic: the same `--seed` gives identical data, anchored to
2026-10-01.

## Configuration

Environment variables, all prefixed `ACME_` (a `.env` file is also read):

| Variable | Default | Purpose |
|---|---|---|
| `ACME_ENVIRONMENT` | `development` | `production` refuses to start without a real JWT secret |
| `ACME_DATABASE_URL` | `sqlite:///./acme.db` | SQLAlchemy URL |
| `ACME_JWT_SECRET` | `change-me-in-production` | HS256 signing key, 32+ bytes in production |
| `ACME_JWT_EXPIRY_HOURS` | `12` | Token lifetime |
| `ACME_CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed frontend origins (JSON list) |
| `ACME_DEMO_PASSWORD` | `acme-demo-2026` | Password given to the seeded demo users |

## Endpoints

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/login`, `GET /auth/me` |
| Employees | `GET/POST /employees`, `GET/PUT /employees/{id}`, `POST /employees/{id}/salary-events`, `/terminate`, `/reactivate` |
| CSV | `GET /employees/export.csv`, `GET /employees/import-template.csv`, `POST /employees/import?dry_run=` |
| Analytics | `GET /analytics/overview`, `/analytics/breakdown?by=`, `/analytics/matrix` |
| Payroll | `GET/POST /payroll-runs`, `GET /payroll-runs/{id}`, `/lines`, `/export.csv` |
| Reference | `GET /reference` (countries, currencies, departments, levels, reasons) |

Every write requires `hr_admin`; reads accept either role.

## Tests and checks

```bash
pytest                          # in-memory SQLite, fixed clock, no network
ruff check app tests scripts
ruff format --check app tests scripts
alembic check                   # models and migrations agree
```

## Docker

```bash
docker build -t acme-api .
docker run -p 8000:8000 -e ACME_JWT_SECRET=<32+ bytes> -e ACME_ENVIRONMENT=production acme-api
```

The entrypoint runs migrations, seeds when empty, then serves. Data lives in `/data`; mount a
volume there to keep it.

## Benchmark

```bash
uvicorn app.main:app --port 8000      # against a seeded database
python scripts/benchmark.py http://127.0.0.1:8000
```

Results and the decisions behind them are in [../../docs/performance.md](../../docs/performance.md).

## Layout

```
app/domain        pure business rules: money, salary history, validation, statistics,
                  analytics, CSV parsing, payroll rules
app/models        SQLAlchemy tables
app/repositories  queries, scoped by organization
app/services      use cases
app/api           routers, schemas, auth dependencies, error mapping
app/seed          deterministic data generator and loader
alembic/          migrations
scripts/          benchmark
tests/            domain/ (pure), api/ (HTTP), seed and config tests
```
