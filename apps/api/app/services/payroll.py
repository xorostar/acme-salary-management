from collections.abc import Iterator
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.csv_io import write_csv
from app.domain.errors import ConflictError, NotFoundError
from app.domain.money import to_major
from app.domain.payroll import Period, build_lines, validate_period
from app.models import PayrollLine, PayrollRun
from app.repositories.exchange_rates import ExchangeRateRepository
from app.repositories.payroll import CountryTotal, PayrollRepository
from app.services.auth import CurrentUser

LINE_COLUMNS = (
    "employee_number", "employee_name", "country_code", "department", "currency_code",
    "annual_salary", "monthly_amount", "rate_to_usd", "monthly_amount_usd",
)  # fmt: skip


class PayrollService:
    def __init__(self, session: Session, *, today: date, user: CurrentUser):
        self.session = session
        self.today = today
        self.user = user
        self.repo = PayrollRepository(session)
        self.rates = ExchangeRateRepository(session)

    def create_run(self, year: int, month: int) -> PayrollRun:
        period = validate_period(year, month, self.today)
        org = self.user.organization_id
        if self.repo.find_for_period(org, year, month):
            raise ConflictError(f"A payroll run for {year}-{month:02d} already exists")

        on = period.end
        lines = build_lines(self.repo.population(org, on), self.rates.rates_as_of(on))
        run = PayrollRun(
            organization_id=org,
            period_year=year,
            period_month=month,
            status="completed",
            employee_count=len(lines),
            total_usd_minor=sum(line.amount_usd_minor for line in lines),
            created_by_user_id=self.user.id,
        )
        try:
            self.repo.add_run(run, lines)
            self.session.commit()
        except IntegrityError:  # a concurrent request created the same period
            self.session.rollback()
            raise ConflictError(f"A payroll run for {year}-{month:02d} already exists") from None
        return run

    def list_runs(self) -> list[PayrollRun]:
        return self.repo.list_runs(self.user.organization_id)

    def get_run(self, run_id: int) -> tuple[PayrollRun, list[CountryTotal]]:
        run = self._require(run_id)
        return run, self.repo.country_totals(run.id)

    def lines(
        self, run_id: int, *, country_code: str | None, page: int, page_size: int
    ) -> tuple[list[PayrollLine], int]:
        run = self._require(run_id)
        return self.repo.lines(run.id, country_code=country_code, page=page, page_size=page_size)

    def export_csv(self, run_id: int) -> tuple[PayrollRun, Iterator[str]]:
        run = self._require(run_id)
        lines = self.repo.all_lines(run.id)
        rows = (
            [
                ln.employee_number, ln.employee_name, ln.country_code, ln.department,
                ln.currency_code, to_major(ln.annual_amount_minor, ln.currency_code),
                to_major(ln.amount_minor, ln.currency_code), ln.rate_to_usd,
                to_major(ln.amount_usd_minor, "USD"),
            ]
            for ln in lines
        )  # fmt: skip
        return run, write_csv(rows, LINE_COLUMNS)

    def _require(self, run_id: int) -> PayrollRun:
        run = self.repo.get(self.user.organization_id, run_id)
        if run is None:
            raise NotFoundError(f"Payroll run {run_id} not found")
        return run


__all__ = ["PayrollService", "Period"]
