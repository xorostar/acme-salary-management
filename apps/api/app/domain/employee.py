"""Employee record validation. Pure, no database access.

Uniqueness (employee_number, email) is enforced by the repository and the
database, not here, because it needs a query.
"""

import re
from dataclasses import dataclass
from datetime import date

from app.domain.errors import FieldError, ValidationError
from app.domain.money import SUPPORTED_CURRENCIES
from app.domain.reference import COUNTRIES, DEPARTMENTS, LEVELS

EMPLOYEE_NUMBER_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,19}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_NAME_LENGTH = 100
MAX_TITLE_LENGTH = 150


@dataclass(frozen=True)
class EmployeeInput:
    employee_number: str
    first_name: str
    last_name: str
    email: str
    country_code: str
    currency_code: str
    department: str
    job_title: str
    level: str
    hire_date: date
    termination_date: date | None = None


def normalize_employee(data: EmployeeInput) -> EmployeeInput:
    """Trim whitespace, upper-case codes, lower-case email. Idempotent."""
    return EmployeeInput(
        employee_number=data.employee_number.strip().upper(),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=data.email.strip().lower(),
        country_code=data.country_code.strip().upper(),
        currency_code=data.currency_code.strip().upper(),
        department=data.department.strip(),
        job_title=data.job_title.strip(),
        level=data.level.strip().upper(),
        hire_date=data.hire_date,
        termination_date=data.termination_date,
    )


def validate_employee(data: EmployeeInput) -> EmployeeInput:
    """Normalize then validate. Returns the normalized input or raises
    ValidationError with every failing field."""
    d = normalize_employee(data)
    errors: list[FieldError] = []

    if not EMPLOYEE_NUMBER_RE.match(d.employee_number):
        errors.append(
            FieldError(
                "employee_number",
                "must be 1-20 letters, digits or hyphens, starting with a letter or digit",
            )
        )
    for field in ("first_name", "last_name"):
        value = getattr(d, field)
        if not value:
            errors.append(FieldError(field, "is required"))
        elif len(value) > MAX_NAME_LENGTH:
            errors.append(FieldError(field, f"must be at most {MAX_NAME_LENGTH} characters"))

    if not EMAIL_RE.match(d.email) or len(d.email) > 254:
        errors.append(FieldError("email", "must be a valid email address"))

    if d.country_code not in COUNTRIES:
        errors.append(FieldError("country_code", f"unsupported country {d.country_code!r}"))
    if d.currency_code not in SUPPORTED_CURRENCIES:
        errors.append(FieldError("currency_code", f"unsupported currency {d.currency_code!r}"))
    if d.department not in DEPARTMENTS:
        errors.append(FieldError("department", f"unknown department {d.department!r}"))
    if d.level not in LEVELS:
        errors.append(FieldError("level", f"unknown level {d.level!r}"))

    if not d.job_title:
        errors.append(FieldError("job_title", "is required"))
    elif len(d.job_title) > MAX_TITLE_LENGTH:
        errors.append(FieldError("job_title", f"must be at most {MAX_TITLE_LENGTH} characters"))

    if d.termination_date is not None and d.termination_date < d.hire_date:
        errors.append(FieldError("termination_date", "cannot be before hire date"))

    if errors:
        raise ValidationError(errors)
    return d


def is_active(termination_date: date | None, as_of: date) -> bool:
    """Active means not terminated on or before the reference date."""
    return termination_date is None or termination_date > as_of
