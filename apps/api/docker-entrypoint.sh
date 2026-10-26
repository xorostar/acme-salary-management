#!/bin/sh
# Bring the schema up to date, seed 10,000 employees if the database is empty,
# then serve. Safe to run on every boot: both steps are idempotent.
set -e

alembic upgrade head
python -m app.seed --if-empty
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
