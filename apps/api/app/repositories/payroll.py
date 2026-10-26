from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.domain.payroll import Line, PayrollInput
from app.models import Employee, PayrollLine, PayrollRun
from app.repositories.employees import active_condition, current_salary_subquery


@dataclass(frozen=True)
class CountryTotal:
    country_code: str
    currency_code: str
    employee_count: int
    amount_minor: int
    amount_usd_minor: int


class PayrollRepository:
    def __init__(self, session: Session):
        self.session = session

    def population(self, org_id: int, on: date) -> list[PayrollInput]:
        """Everyone employed on `on`, with the annual salary in force that day."""
        amount = current_salary_subquery(on).label("amount")
        stmt = (
            select(
                Employee.id,
                Employee.employee_number,
                Employee.first_name,
                Employee.last_name,
                Employee.country_code,
                Employee.department,
                Employee.currency_code,
                amount,
            )
            .where(
                Employee.organization_id == org_id,
                Employee.hire_date <= on,
                active_condition(on),
            )
            .order_by(Employee.employee_number)
        )
        return [
            PayrollInput(eid, number, f"{first} {last}", country, dept, currency, amt)
            for eid, number, first, last, country, dept, currency, amt in self.session.execute(stmt)
            if amt is not None
        ]

    def find_for_period(self, org_id: int, year: int, month: int) -> PayrollRun | None:
        stmt = select(PayrollRun).where(
            PayrollRun.organization_id == org_id,
            PayrollRun.period_year == year,
            PayrollRun.period_month == month,
        )
        return self.session.scalars(stmt).first()

    def get(self, org_id: int, run_id: int) -> PayrollRun | None:
        stmt = select(PayrollRun).where(
            PayrollRun.id == run_id, PayrollRun.organization_id == org_id
        )
        return self.session.scalars(stmt).first()

    def list_runs(self, org_id: int) -> list[PayrollRun]:
        stmt = (
            select(PayrollRun)
            .where(PayrollRun.organization_id == org_id)
            .order_by(PayrollRun.period_year.desc(), PayrollRun.period_month.desc())
        )
        return list(self.session.scalars(stmt))

    def add_run(self, run: PayrollRun, lines: list[Line]) -> PayrollRun:
        self.session.add(run)
        self.session.flush()
        if lines:
            self.session.execute(
                insert(PayrollLine),
                [{"payroll_run_id": run.id, **line.__dict__} for line in lines],
            )
        return run

    def country_totals(self, run_id: int) -> list[CountryTotal]:
        stmt = (
            select(
                PayrollLine.country_code,
                PayrollLine.currency_code,
                func.count(PayrollLine.id),
                func.sum(PayrollLine.amount_minor),
                func.sum(PayrollLine.amount_usd_minor),
            )
            .where(PayrollLine.payroll_run_id == run_id)
            .group_by(PayrollLine.country_code, PayrollLine.currency_code)
            .order_by(func.sum(PayrollLine.amount_usd_minor).desc())
        )
        return [CountryTotal(*row) for row in self.session.execute(stmt)]

    def lines(
        self, run_id: int, *, country_code: str | None, page: int, page_size: int
    ) -> tuple[list[PayrollLine], int]:
        base = select(PayrollLine).where(PayrollLine.payroll_run_id == run_id)
        if country_code:
            base = base.where(PayrollLine.country_code == country_code)
        total = self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        stmt = (
            base.order_by(PayrollLine.employee_number)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(stmt)), total

    def all_lines(self, run_id: int) -> list[PayrollLine]:
        stmt = (
            select(PayrollLine)
            .where(PayrollLine.payroll_run_id == run_id)
            .order_by(PayrollLine.employee_number)
        )
        return list(self.session.scalars(stmt))
