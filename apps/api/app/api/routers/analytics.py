"""Compensation analytics. All amounts are integers in minor units; USD
figures use the planning rate in force on `as_of`."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import CurrentUserDep, SessionDep, TodayDep
from app.domain.errors import ValidationError
from app.domain.reference import COUNTRIES
from app.domain.stats import Summary
from app.repositories.employees import EmployeeFilters
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

DimensionParam = Literal["country_code", "department", "level"]


class SummaryOut(BaseModel):
    count: int
    total: int
    mean: int
    min: int
    max: int
    p10: int
    p25: int
    p50: int
    p75: int
    p90: int

    @classmethod
    def of(cls, s: Summary | None) -> "SummaryOut | None":
        return cls(**s.__dict__) if s else None


class BucketOut(BaseModel):
    start: int
    end: int
    count: int


class RateOut(BaseModel):
    currency_code: str
    rate_to_usd: str
    effective_date: date


class OverviewOut(BaseModel):
    as_of: date
    currency_code: str = "USD"
    headcount: int
    annual_payroll_usd: SummaryOut | None
    histogram: list[BucketOut]
    rates: list[RateOut]
    missing_rates: list[str]


class GroupOut(BaseModel):
    key: str
    label: str
    usd: SummaryOut
    local_currency: str | None
    local: SummaryOut | None


class BreakdownOut(BaseModel):
    as_of: date
    dimension: DimensionParam
    groups: list[GroupOut]
    missing_rates: list[str]


class CellOut(BaseModel):
    row: str
    col: str
    count: int
    median_usd: int


class MatrixOut(BaseModel):
    as_of: date
    rows: DimensionParam
    cols: DimensionParam
    cells: list[CellOut]
    missing_rates: list[str]


def _label(dimension: str, key: str) -> str:
    if dimension == "country_code" and key in COUNTRIES:
        return COUNTRIES[key].name
    return key


def _filters(country_code: str | None, department: str | None, level: str | None):
    return EmployeeFilters(country_code=country_code, department=department, level=level)


CountryQ = Annotated[str | None, Query(max_length=2)]
DepartmentQ = Annotated[str | None, Query(max_length=100)]
LevelQ = Annotated[str | None, Query(max_length=10)]


@router.get("/overview", response_model=OverviewOut)
def overview(
    session: SessionDep,
    today: TodayDep,
    user: CurrentUserDep,
    country_code: CountryQ = None,
    department: DepartmentQ = None,
    level: LevelQ = None,
    bins: Annotated[int, Query(ge=1, le=100)] = 20,
) -> OverviewOut:
    o = AnalyticsService(session, today=today, user=user).overview(
        _filters(country_code, department, level), bins=bins
    )
    return OverviewOut(
        as_of=o.as_of,
        headcount=o.summary.count if o.summary else 0,
        annual_payroll_usd=SummaryOut.of(o.summary),
        histogram=[BucketOut(**b.__dict__) for b in o.histogram],
        rates=[RateOut(**r.__dict__) for r in o.rates],
        missing_rates=sorted(o.missing_currencies),
    )


@router.get("/breakdown", response_model=BreakdownOut)
def breakdown(
    session: SessionDep,
    today: TodayDep,
    user: CurrentUserDep,
    by: DimensionParam = "country_code",
    country_code: CountryQ = None,
    department: DepartmentQ = None,
    level: LevelQ = None,
) -> BreakdownOut:
    b = AnalyticsService(session, today=today, user=user).breakdown(
        _filters(country_code, department, level), by
    )
    return BreakdownOut(
        as_of=b.as_of,
        dimension=by,
        groups=[
            GroupOut(
                key=g.key,
                label=_label(by, g.key),
                usd=SummaryOut.of(g.usd),
                local_currency=g.local_currency,
                local=SummaryOut.of(g.local),
            )
            for g in b.groups
        ],
        missing_rates=sorted(b.missing_currencies),
    )


@router.get("/matrix", response_model=MatrixOut)
def matrix(
    session: SessionDep,
    today: TodayDep,
    user: CurrentUserDep,
    rows: DimensionParam = "level",
    cols: DimensionParam = "country_code",
    country_code: CountryQ = None,
    department: DepartmentQ = None,
    level: LevelQ = None,
) -> MatrixOut:
    if rows == cols:
        raise ValidationError.single("cols", "must differ from rows")
    m = AnalyticsService(session, today=today, user=user).matrix(
        _filters(country_code, department, level), rows, cols
    )
    return MatrixOut(
        as_of=m.as_of,
        rows=rows,
        cols=cols,
        cells=[
            CellOut(row=c.row, col=c.col, count=c.count, median_usd=c.median_usd_minor)
            for c in m.cells
        ],  # fmt: skip
        missing_rates=sorted(m.missing_currencies),
    )
