"""CLI: `python -m app.seed [--reset] [--count N] [--seed S]`.

Run `alembic upgrade head` first. The demo password comes from
ACME_DEMO_PASSWORD and defaults to the value printed in the README.
"""

import argparse
import os
import sys
import time

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.seed import (
    DEMO_ADMIN_EMAIL,
    DEMO_VIEWER_EMAIL,
    DatabaseNotEmptyError,
    seed_database,
)
from app.seed.generator import DEFAULT_COUNT, DEFAULT_SEED

DEFAULT_DEMO_PASSWORD = "acme-demo-2026"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the ACME salary database")
    parser.add_argument("--reset", action="store_true", help="delete existing data first")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="exit successfully without changes when data already exists (for deploys)",
    )
    args = parser.parse_args(argv)

    password = os.environ.get("ACME_DEMO_PASSWORD", DEFAULT_DEMO_PASSWORD)
    engine = make_engine(get_settings().database_url)
    started = time.perf_counter()
    with make_session_factory(engine)() as session:
        try:
            result = seed_database(
                session, demo_password=password, count=args.count, seed=args.seed,
                reset=args.reset,
            )  # fmt: skip
        except DatabaseNotEmptyError as exc:
            if args.if_empty:
                print("Database already seeded; nothing to do.")
                return 0
            print(exc, file=sys.stderr)
            return 1
    elapsed = time.perf_counter() - started

    print(
        f"Seeded {result.employees:,} employees, {result.salary_events:,} salary events and "
        f"{result.exchange_rates} exchange rates in {elapsed:.1f}s."
    )
    print(f"Log in as {DEMO_ADMIN_EMAIL} (admin) or {DEMO_VIEWER_EMAIL} (read-only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
