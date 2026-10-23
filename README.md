# ACME Salary Management

Web-based salary management for an HR manager at a 10,000-employee, multi-country organization. Replaces spreadsheet-based salary tracking with a system that keeps salary history, runs payroll snapshots, and answers compensation questions in one normalized currency.

Built as a take-home assessment. Start with the docs:

| Document | What it covers |
|---|---|
| [docs/requirements.md](docs/requirements.md) | Goal, scope, deliberate exclusions |
| [docs/architecture.md](docs/architecture.md) | System shape, data model, key decisions |
| [docs/decisions/](docs/decisions/) | Architecture decision records |
| [docs/ai-usage.md](docs/ai-usage.md) | How AI tools were used, prompts, and what was verified by hand |
| [docs/performance.md](docs/performance.md) | Measurements and performance trade-offs |

## Layout

```
apps/api   Python backend (FastAPI, SQLAlchemy, SQLite)
apps/web   Next.js frontend (JavaScript)
docs       Requirements, architecture, decisions, AI usage log
```

## Running locally

See [apps/api/README.md](apps/api/README.md) and [apps/web/README.md](apps/web/README.md).
