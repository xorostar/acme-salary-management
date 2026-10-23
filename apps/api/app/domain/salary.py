"""Salary history rules (ADR 003).

Pure functions over plain values so they can be tested without a database.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.domain.errors import FieldError, ValidationError
from app.domain.money import SUPPORTED_CURRENCIES

MAX_REASON_LENGTH = 200
MAX_ANNUAL_AMOUNT_MINOR = 10**13  # generous sanity cap: 100 billion in 2-decimal currencies


@dataclass(frozen=True, order=True)
class SalaryPoint:
    """A salary that applies from effective_date onward."""

    effective_date: date
    annual_amount_minor: int
    currency_code: str


def current_salary(events: Iterable[SalaryPoint], as_of: date) -> SalaryPoint | None:
    """The salary in force on `as_of`: the latest event dated on or before it.

    Future-dated events are ignored. Returns None if no event applies yet.
    """
    applicable = [e for e in events if e.effective_date <= as_of]
    if not applicable:
        return None
    return max(applicable, key=lambda e: e.effective_date)


def validate_salary_event(
    *,
    hire_date: date,
    employee_currency: str,
    existing_effective_dates: Iterable[date],
    annual_amount_minor: int,
    currency_code: str,
    effective_date: date,
    reason: str,
) -> None:
    """Raise ValidationError listing every rule the new event breaks."""
    errors: list[FieldError] = []

    if not isinstance(annual_amount_minor, int) or isinstance(annual_amount_minor, bool):
        errors.append(FieldError("annual_amount_minor", "must be an integer in minor units"))
    elif annual_amount_minor <= 0:
        errors.append(FieldError("annual_amount_minor", "must be greater than zero"))
    elif annual_amount_minor > MAX_ANNUAL_AMOUNT_MINOR:
        errors.append(FieldError("annual_amount_minor", "exceeds the maximum supported amount"))

    if currency_code not in SUPPORTED_CURRENCIES:
        errors.append(FieldError("currency_code", f"unsupported currency {currency_code!r}"))
    elif currency_code != employee_currency:
        errors.append(
            FieldError(
                "currency_code",
                f"must match the employee's currency {employee_currency}; "
                "change the employee's currency first to relocate them",
            )
        )

    if effective_date < hire_date:
        errors.append(
            FieldError("effective_date", f"cannot be before hire date {hire_date.isoformat()}")
        )
    if effective_date in set(existing_effective_dates):
        errors.append(
            FieldError(
                "effective_date",
                "a salary event already exists on this date; record a correction on a new date",
            )
        )

    cleaned_reason = reason.strip() if isinstance(reason, str) else ""
    if not cleaned_reason:
        errors.append(FieldError("reason", "is required"))
    elif len(cleaned_reason) > MAX_REASON_LENGTH:
        errors.append(FieldError("reason", f"must be at most {MAX_REASON_LENGTH} characters"))

    if errors:
        raise ValidationError(errors)
