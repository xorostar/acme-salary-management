"""Small builders for test data. Each returns a persisted ORM object."""

from datetime import date

from sqlalchemy.orm import Session

from app.domain.reference import ROLE_ADMIN, ROLE_VIEWER
from app.models import Employee, ExchangeRate, Organization, SalaryEvent, User
from app.security import hash_password

# bcrypt is slow by design; hash the shared test password once per process.
TEST_PASSWORD = "Password123!"
_TEST_HASH = hash_password(TEST_PASSWORD)


def make_org(session: Session, name: str = "ACME", base_currency: str = "USD") -> Organization:
    org = Organization(name=name, base_currency=base_currency)
    session.add(org)
    session.flush()
    return org


def make_user(
    session: Session,
    org: Organization,
    *,
    email: str = "admin@acme.example",
    role: str = ROLE_ADMIN,
    full_name: str = "Test User",
) -> User:
    user = User(
        organization_id=org.id,
        email=email,
        password_hash=_TEST_HASH,
        full_name=full_name,
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def make_admin(session: Session, org: Organization) -> User:
    return make_user(session, org, email="admin@acme.example", role=ROLE_ADMIN)


def make_viewer(session: Session, org: Organization) -> User:
    return make_user(session, org, email="viewer@acme.example", role=ROLE_VIEWER)


_counter = {"n": 0}


def make_employee(
    session: Session,
    org: Organization,
    *,
    employee_number: str | None = None,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    email: str | None = None,
    country_code: str = "US",
    currency_code: str = "USD",
    department: str = "Engineering",
    job_title: str = "Software Engineer",
    level: str = "L3",
    hire_date: date = date(2021, 3, 1),
    termination_date: date | None = None,
    salary: int | None = 10000000,
    salary_effective: date | None = None,
) -> Employee:
    _counter["n"] += 1
    n = _counter["n"]
    emp = Employee(
        organization_id=org.id,
        employee_number=employee_number or f"E{n:05d}",
        first_name=first_name,
        last_name=last_name,
        email=email or f"employee{n}@acme.example",
        country_code=country_code,
        currency_code=currency_code,
        department=department,
        job_title=job_title,
        level=level,
        hire_date=hire_date,
        termination_date=termination_date,
    )
    session.add(emp)
    session.flush()
    if salary is not None:
        session.add(
            SalaryEvent(
                organization_id=org.id,
                employee_id=emp.id,
                annual_amount_minor=salary,
                currency_code=currency_code,
                effective_date=salary_effective or hire_date,
                reason="Hire",
            )
        )
        session.flush()
    return emp


def make_rate(
    session: Session, currency_code: str, rate: str, effective: date = date(2025, 1, 1)
) -> ExchangeRate:
    r = ExchangeRate(currency_code=currency_code, rate_to_usd=rate, effective_date=effective)
    session.add(r)
    session.flush()
    return r
