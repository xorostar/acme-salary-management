from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.domain.analytics import PayRecord
from app.models import Employee, SalaryEvent

SortField = Literal[
    "last_name",
    "employee_number",
    "hire_date",
    "department",
    "country_code",
    "level",
    "current_salary",
]
Status = Literal["active", "terminated", "all"]


@dataclass(frozen=True)
class EmployeeFilters:
    q: str | None = None
    country_code: str | None = None
    department: str | None = None
    level: str | None = None
    status: Status = "active"


@dataclass(frozen=True)
class EmployeeRow:
    """An employee plus their salary in force on the reference date."""

    employee: Employee
    current_amount_minor: int | None
    current_effective_date: date | None


def current_salary_subquery(as_of: date):
    """Correlated scalar subquery: latest salary event on or before `as_of`.

    Uses the (employee_id, effective_date) index; one index seek per row.
    """
    return (
        select(SalaryEvent.annual_amount_minor)
        .where(SalaryEvent.employee_id == Employee.id, SalaryEvent.effective_date <= as_of)
        .order_by(SalaryEvent.effective_date.desc())
        .limit(1)
        .scalar_subquery()
    )


def current_effective_date_subquery(as_of: date):
    return (
        select(func.max(SalaryEvent.effective_date))
        .where(SalaryEvent.employee_id == Employee.id, SalaryEvent.effective_date <= as_of)
        .scalar_subquery()
    )


def active_condition(as_of: date):
    return or_(Employee.termination_date.is_(None), Employee.termination_date > as_of)


def apply_filters(stmt: Select, org_id: int, filters: EmployeeFilters, as_of: date) -> Select:
    stmt = stmt.where(Employee.organization_id == org_id)
    if filters.country_code:
        stmt = stmt.where(Employee.country_code == filters.country_code)
    if filters.department:
        stmt = stmt.where(Employee.department == filters.department)
    if filters.level:
        stmt = stmt.where(Employee.level == filters.level)
    if filters.status == "active":
        stmt = stmt.where(active_condition(as_of))
    elif filters.status == "terminated":
        stmt = stmt.where(
            and_(Employee.termination_date.is_not(None), Employee.termination_date <= as_of)
        )
    if filters.q:
        term = filters.q.strip()
        if term:
            like = f"%{term}%"
            stmt = stmt.where(
                or_(
                    Employee.employee_number.ilike(f"{term}%"),
                    Employee.first_name.ilike(like),
                    Employee.last_name.ilike(like),
                    Employee.email.ilike(like),
                    (Employee.first_name + " " + Employee.last_name).ilike(like),
                )
            )
    return stmt


class EmployeeRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, org_id: int, employee_id: int) -> Employee | None:
        stmt = select(Employee).where(
            Employee.id == employee_id, Employee.organization_id == org_id
        )
        return self.session.scalars(stmt).first()

    def number_exists(
        self, org_id: int, employee_number: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(Employee.id).where(
            Employee.organization_id == org_id, Employee.employee_number == employee_number
        )
        if exclude_id is not None:
            stmt = stmt.where(Employee.id != exclude_id)
        return self.session.scalars(stmt).first() is not None

    def email_exists(self, org_id: int, email: str, exclude_id: int | None = None) -> bool:
        stmt = select(Employee.id).where(
            Employee.organization_id == org_id, Employee.email == email
        )
        if exclude_id is not None:
            stmt = stmt.where(Employee.id != exclude_id)
        return self.session.scalars(stmt).first() is not None

    def existing_numbers(self, org_id: int, numbers: list[str]) -> set[str]:
        if not numbers:
            return set()
        stmt = select(Employee.employee_number).where(
            Employee.organization_id == org_id, Employee.employee_number.in_(numbers)
        )
        return set(self.session.scalars(stmt))

    def existing_emails(self, org_id: int, emails: list[str]) -> set[str]:
        if not emails:
            return set()
        stmt = select(Employee.email).where(
            Employee.organization_id == org_id, Employee.email.in_(emails)
        )
        return set(self.session.scalars(stmt))

    def add(self, employee: Employee) -> Employee:
        self.session.add(employee)
        self.session.flush()
        return employee

    def count(self, org_id: int, filters: EmployeeFilters, as_of: date) -> int:
        stmt = apply_filters(select(func.count(Employee.id)), org_id, filters, as_of)
        return self.session.scalar(stmt) or 0

    def search(
        self,
        org_id: int,
        filters: EmployeeFilters,
        as_of: date,
        *,
        page: int,
        page_size: int,
        sort: SortField = "last_name",
        descending: bool = False,
    ) -> list[EmployeeRow]:
        # Two phases (a "deferred join"): pick the page of ids using only
        # employee columns, then fetch rows and current salary for those ids.
        # The correlated salary subqueries then run 25 times, not once per
        # row skipped by OFFSET. Sorting by salary needs the subquery in phase 1.
        if sort == "current_salary":
            order_col = current_salary_subquery(as_of)
        else:
            order_col = getattr(Employee, sort)
        order = order_col.desc() if descending else order_col.asc()
        id_stmt = (
            apply_filters(select(Employee.id), org_id, filters, as_of)
            .order_by(order, Employee.id.asc())  # tie-break on id so paging is stable
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        ids = list(self.session.scalars(id_stmt))
        if not ids:
            return []

        amount = current_salary_subquery(as_of).label("current_amount")
        effective = current_effective_date_subquery(as_of).label("current_effective")
        rows = {
            emp.id: EmployeeRow(emp, amt, eff)
            for emp, amt, eff in self.session.execute(
                select(Employee, amount, effective).where(Employee.id.in_(ids))
            )
        }
        return [rows[i] for i in ids]

    def current_pay(self, org_id: int, filters: EmployeeFilters, as_of: date) -> list[PayRecord]:
        """Salary in force on `as_of` for every matching employee, as plain records.

        Employees with no salary event on or before `as_of` (hired in the
        future) are skipped. One query with a correlated subquery that seeks
        the (employee_id, effective_date) index once per employee. A grouped
        join was measured as about twice as slow on SQLite, because the planner
        builds a temporary index for it (docs/performance.md).
        """
        amount = current_salary_subquery(as_of).label("amount")
        stmt = apply_filters(
            select(
                Employee.country_code,
                Employee.department,
                Employee.level,
                Employee.currency_code,
                amount,
            ),
            org_id,
            filters,
            as_of,
        )
        return [
            PayRecord(country, dept, level, currency, amt)
            for country, dept, level, currency, amt in self.session.execute(stmt)
            if amt is not None
        ]
