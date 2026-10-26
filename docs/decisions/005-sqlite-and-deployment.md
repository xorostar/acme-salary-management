# ADR 005: SQLite in all environments, deployed on a persistent volume

**Status:** Accepted

## Context

The brief allows any relational database and suggests SQLite. The workload is 10,000 employees, a handful of HR users, and mostly reads.

## Decision

SQLite everywhere: in-memory for tests, a file for local development, and a file on a Fly.io persistent volume in production. WAL journal mode is enabled. SQLAlchemy is the only database interface so a switch to PostgreSQL is a connection string and a migration run.

## Reasoning

- **Same engine in tests, dev, and prod.** No "works on SQLite, breaks on Postgres" surprises, and no test database provisioning.
- **The data is small.** 10,000 employees with a few salary events each is a few megabytes. SQLite handles aggregates over this in single-digit milliseconds with the right indexes.
- **Concurrency profile fits.** A few HR users with occasional writes is exactly SQLite's sweet spot under WAL mode.
- **Operationally trivial.** One file to back up. No managed database bill for an assessment.

## Trade-offs accepted

- A single API instance. Horizontal scaling would require moving to PostgreSQL. Documented, and the SQLAlchemy layer makes it a configuration change.
- Fly.io volumes are tied to one region and one machine. Acceptable for the stated scale.
- SQLite has no native `percentile` function. Salaries have to be converted to USD per currency first anyway, so percentiles are computed in Python on the converted integers (`app/domain/stats.py`). That takes about a millisecond for the whole org and is tested against hand-computed values. On PostgreSQL, `percentile_cont` would be an option.

## Update, 26 Oct 2026: hosting the demo for free

Fly.io no longer offers a free plan to new accounts, and the demo should cost nothing. The
API is deployed to Render's free plan instead, from the same Dockerfile. That plan has no
persistent disk, so the SQLite file lives inside the container and is re-created from the
seed on every boot. For a public demo this is a feature: every reviewer starts from the
same clean data. For real use, the same image runs with a disk attached (Render paid plan
or Fly.io with a volume, `fly.toml` is kept for that) and nothing else changes.
