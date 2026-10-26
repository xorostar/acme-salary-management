"""Load the generated organization into a database.

Inserts go through SQLAlchemy Core in batches with explicit ids, which loads
10,000 employees and ~40,000 salary events in a few seconds on SQLite.
"""

from dataclasses import dataclass

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.domain.reference import ROLE_ADMIN, ROLE_VIEWER
from app.models import (
    Employee,
    ExchangeRate,
    Organization,
    PayrollLine,
    PayrollRun,
    SalaryEvent,
    User,
)
from app.security import hash_password
from app.seed.generator import (
    ANCHOR_DATE,
    DEFAULT_COUNT,
    DEFAULT_SEED,
    RATES,
    generate_employees,
)

DEMO_ADMIN_EMAIL = "admin@acme.example"
DEMO_VIEWER_EMAIL = "viewer@acme.example"
BATCH = 2_000


@dataclass(frozen=True)
class SeedResult:
    organization_id: int
    employees: int
    salary_events: int
    exchange_rates: int


class DatabaseNotEmptyError(RuntimeError):
    pass


def reset_database(session: Session) -> None:
    """Delete all rows in foreign-key order. Keeps the schema and migration state."""
    for model in (PayrollLine, PayrollRun, SalaryEvent, Employee, User, ExchangeRate,
                  Organization):  # fmt: skip
        session.execute(delete(model))
    session.flush()


def seed_database(
    session: Session,
    *,
    demo_password: str,
    count: int = DEFAULT_COUNT,
    seed: int = DEFAULT_SEED,
    reset: bool = False,
) -> SeedResult:
    if reset:
        reset_database(session)
    elif session.scalar(select(func.count(Organization.id))):
        raise DatabaseNotEmptyError("Database already has data; pass --reset to replace it")

    org = Organization(name="ACME", base_currency="USD")
    session.add(org)
    session.flush()

    password_hash = hash_password(demo_password)
    session.add_all(
        [
            User(organization_id=org.id, email=DEMO_ADMIN_EMAIL, password_hash=password_hash,
                 full_name="Hana Admin", role=ROLE_ADMIN),
            User(organization_id=org.id, email=DEMO_VIEWER_EMAIL, password_hash=password_hash,
                 full_name="Victor Viewer", role=ROLE_VIEWER),
        ]
    )  # fmt: skip
    session.flush()

    rate_rows = [
        {"currency_code": code, "rate_to_usd": rate, "effective_date": effective}
        for effective, rates in RATES.items()
        for code, rate in rates.items()
    ]
    session.execute(insert(ExchangeRate), rate_rows)

    people = generate_employees(count, seed=seed, anchor=ANCHOR_DATE)
    emp_rows: list[dict] = []
    event_rows: list[dict] = []
    for emp_id, p in enumerate(people, start=1):
        emp_rows.append(
            {
                "id": emp_id,
                "organization_id": org.id,
                "employee_number": p.employee_number,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "email": p.email,
                "country_code": p.country_code,
                "currency_code": p.currency_code,
                "department": p.department,
                "job_title": p.job_title,
                "level": p.level,
                "hire_date": p.hire_date,
                "termination_date": p.termination_date,
                "version": 1,
            }
        )
        for e in p.salary_events:
            event_rows.append(
                {
                    "organization_id": org.id,
                    "employee_id": emp_id,
                    "annual_amount_minor": e.annual_amount_minor,
                    "currency_code": p.currency_code,
                    "effective_date": e.effective_date,
                    "reason": e.reason,
                    "created_by_user_id": None,
                }
            )

    for i in range(0, len(emp_rows), BATCH):
        session.execute(insert(Employee), emp_rows[i : i + BATCH])
    for i in range(0, len(event_rows), BATCH):
        session.execute(insert(SalaryEvent), event_rows[i : i + BATCH])
    session.commit()

    return SeedResult(
        organization_id=org.id,
        employees=len(emp_rows),
        salary_events=len(event_rows),
        exchange_rates=len(rate_rows),
    )
