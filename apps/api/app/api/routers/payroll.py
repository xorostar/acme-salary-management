from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUserDep, SessionDep, TodayDep, require_role
from app.domain.reference import COUNTRIES, ROLE_ADMIN
from app.models import PayrollLine, PayrollRun
from app.repositories.payroll import CountryTotal
from app.services.auth import CurrentUser
from app.services.payroll import PayrollService

router = APIRouter(prefix="/payroll-runs", tags=["payroll"])

AdminDep = Annotated[CurrentUser, Depends(require_role(ROLE_ADMIN))]


class RunCreateIn(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class RunOut(BaseModel):
    id: int
    period_year: int
    period_month: int
    status: str
    employee_count: int
    total_usd_minor: int
    created_at: datetime

    @classmethod
    def of(cls, run: PayrollRun) -> "RunOut":
        return cls(
            id=run.id,
            period_year=run.period_year,
            period_month=run.period_month,
            status=run.status,
            employee_count=run.employee_count,
            total_usd_minor=run.total_usd_minor,
            created_at=run.created_at,
        )


class CountryTotalOut(BaseModel):
    country_code: str
    country_name: str
    currency_code: str
    employee_count: int
    amount_minor: int
    amount_usd_minor: int

    @classmethod
    def of(cls, t: CountryTotal) -> "CountryTotalOut":
        country = COUNTRIES.get(t.country_code)
        return cls(country_name=country.name if country else t.country_code, **t.__dict__)


class RunDetailOut(RunOut):
    countries: list[CountryTotalOut]


class LineOut(BaseModel):
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

    @classmethod
    def of(cls, ln: PayrollLine) -> "LineOut":
        return cls(**{f: getattr(ln, f) for f in cls.model_fields})


class LinesOut(BaseModel):
    items: list[LineOut]
    page: int
    page_size: int
    total: int


def _service(session, today, user) -> PayrollService:
    return PayrollService(session, today=today, user=user)


@router.get("", response_model=list[RunOut])
def list_runs(session: SessionDep, today: TodayDep, user: CurrentUserDep) -> list[RunOut]:
    return [RunOut.of(r) for r in _service(session, today, user).list_runs()]


@router.post("", response_model=RunDetailOut, status_code=status.HTTP_201_CREATED)
def create_run(
    body: RunCreateIn, session: SessionDep, today: TodayDep, user: AdminDep
) -> RunDetailOut:
    service = _service(session, today, user)
    run = service.create_run(body.year, body.month)
    run, totals = service.get_run(run.id)
    return RunDetailOut(**RunOut.of(run).model_dump(),
                        countries=[CountryTotalOut.of(t) for t in totals])  # fmt: skip


@router.get("/{run_id}", response_model=RunDetailOut)
def get_run(run_id: int, session: SessionDep, today: TodayDep, user: CurrentUserDep):
    run, totals = _service(session, today, user).get_run(run_id)
    return RunDetailOut(**RunOut.of(run).model_dump(),
                        countries=[CountryTotalOut.of(t) for t in totals])  # fmt: skip


@router.get("/{run_id}/lines", response_model=LinesOut)
def run_lines(
    run_id: int,
    session: SessionDep,
    today: TodayDep,
    user: CurrentUserDep,
    country_code: Annotated[str | None, Query(max_length=2)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> LinesOut:
    items, total = _service(session, today, user).lines(
        run_id, country_code=country_code, page=page, page_size=page_size
    )
    return LinesOut(items=[LineOut.of(i) for i in items], page=page, page_size=page_size,
                    total=total)  # fmt: skip


@router.get("/{run_id}/export.csv", response_class=StreamingResponse)
def export_run(run_id: int, session: SessionDep, today: TodayDep, user: CurrentUserDep):
    run, chunks = _service(session, today, user).export_csv(run_id)
    name = f"acme-payroll-{run.period_year}-{run.period_month:02d}.csv"
    return StreamingResponse(
        chunks,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
