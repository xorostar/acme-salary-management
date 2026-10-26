"""Monthly payroll run rules. Pure functions.

A run is a frozen record of what each employee is owed for one month. It
records; it does not pay (see requirements, "deliberately out of scope").

Rules:
- Included: everyone employed on the last day of the period.
- Amount: the annual salary in force on that day, divided by 12, rounded
  half-up to a whole minor unit. No proration for mid-month joiners or
  leavers (documented trade-off in docs/requirements.md).
- USD: converted with the planning rate in force on that day.
- Periods may be at most one month ahead of the current month, so HR can
  prepare next month's run but cannot create runs years in the future.
"""

import calendar
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.errors import FieldError, ValidationError
from app.domain.money import RateConverter, monthly_from_annual

EARLIEST_YEAR = 2000


@dataclass(frozen=True)
class Period:
    year: int
    month: int

    @property
    def start(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def end(self) -> date:
        return date(self.year, self.month, calendar.monthrange(self.year, self.month)[1])

    def months_after(self, other: "Period") -> int:
        return (self.year - other.year) * 12 + (self.month - other.month)


def validate_period(year: int, month: int, today: date) -> Period:
    errors: list[FieldError] = []
    if not 1 <= month <= 12:
        errors.append(FieldError("month", "must be between 1 and 12"))
    if year < EARLIEST_YEAR:
        errors.append(FieldError("year", f"must be {EARLIEST_YEAR} or later"))
    if errors:
        raise ValidationError(errors)
    period = Period(year, month)
    if period.months_after(Period(today.year, today.month)) > 1:
        raise ValidationError.single("month", "can be at most one month ahead of the current month")
    return period


@dataclass(frozen=True)
class PayrollInput:
    """One employee employed on the period end, with the salary in force then."""

    employee_id: int
    employee_number: str
    employee_name: str
    country_code: str
    department: str
    currency_code: str
    annual_amount_minor: int


@dataclass(frozen=True)
class Line:
    employee_id: int
    employee_number: str
    employee_name: str
    country_code: str
    department: str
    currency_code: str
    annual_amount_minor: int
    amount_minor: int
    amount_usd_minor: int
    rate_to_usd: str


def build_lines(people: Iterable[PayrollInput], rates: dict[str, Decimal]) -> list[Line]:
    """One line per person. Raises if any currency lacks a rate: a payroll
    record must never guess a conversion."""
    people = list(people)
    missing = sorted({p.currency_code for p in people} - set(rates))
    if missing:
        raise ValidationError.single("rates", f"no planning rate in force for {', '.join(missing)}")
    converters = {c: RateConverter.build(c, "USD", r) for c, r in rates.items()}
    lines = []
    for p in people:
        monthly = monthly_from_annual(p.annual_amount_minor)
        lines.append(
            Line(
                employee_id=p.employee_id,
                employee_number=p.employee_number,
                employee_name=p.employee_name,
                country_code=p.country_code,
                department=p.department,
                currency_code=p.currency_code,
                annual_amount_minor=p.annual_amount_minor,
                amount_minor=monthly,
                amount_usd_minor=converters[p.currency_code](monthly),
                rate_to_usd=str(rates[p.currency_code]),
            )
        )
    return lines
