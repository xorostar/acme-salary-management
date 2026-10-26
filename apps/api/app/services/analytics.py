from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.analytics import (
    Conversion,
    Dimension,
    GroupSummary,
    MatrixCell,
    convert_to_usd,
    median_matrix,
    summarize_by,
    usd_histogram,
)
from app.domain.stats import Bucket, Summary, summarize
from app.repositories.employees import EmployeeFilters, EmployeeRepository
from app.repositories.exchange_rates import ExchangeRateRepository
from app.services.auth import CurrentUser


@dataclass(frozen=True)
class RateInfo:
    currency_code: str
    rate_to_usd: str
    effective_date: date


@dataclass(frozen=True)
class Overview:
    as_of: date
    summary: Summary | None
    histogram: list[Bucket]
    rates: list[RateInfo]
    missing_currencies: frozenset[str]


@dataclass(frozen=True)
class Breakdown:
    as_of: date
    dimension: Dimension
    groups: list[GroupSummary]
    missing_currencies: frozenset[str]


@dataclass(frozen=True)
class Matrix:
    as_of: date
    rows: Dimension
    cols: Dimension
    cells: list[MatrixCell]
    missing_currencies: frozenset[str]


class AnalyticsService:
    """Questions about how the org pays people, always over active employees
    and the salary in force on the reference date."""

    def __init__(self, session: Session, *, today: date, user: CurrentUser):
        self.today = today
        self.user = user
        self.employees = EmployeeRepository(session)
        self.rates = ExchangeRateRepository(session)

    def _population(self, filters: EmployeeFilters) -> Conversion:
        active = EmployeeFilters(
            country_code=filters.country_code,
            department=filters.department,
            level=filters.level,
            status="active",
        )
        records = self.employees.current_pay(self.user.organization_id, active, self.today)
        return convert_to_usd(records, self._rates())

    def _rates(self) -> dict[str, Decimal]:
        return self.rates.rates_as_of(self.today)

    def overview(self, filters: EmployeeFilters, *, bins: int = 20) -> Overview:
        pop = self._population(filters)
        values = [c.usd_minor for c in pop.converted]
        return Overview(
            as_of=self.today,
            summary=summarize(values),
            histogram=usd_histogram(pop.converted, bins),
            rates=[RateInfo(c, r, d) for c, r, d in self.rates.rates_in_force(self.today)],
            missing_currencies=pop.missing_currencies,
        )

    def breakdown(self, filters: EmployeeFilters, dimension: Dimension) -> Breakdown:
        pop = self._population(filters)
        return Breakdown(
            self.today, dimension, summarize_by(pop.converted, dimension), pop.missing_currencies
        )

    def matrix(self, filters: EmployeeFilters, rows: Dimension, cols: Dimension) -> Matrix:
        pop = self._population(filters)
        return Matrix(
            self.today, rows, cols, median_matrix(pop.converted, rows, cols),
            pop.missing_currencies,
        )  # fmt: skip
