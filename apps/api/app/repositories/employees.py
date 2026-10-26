from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

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
        amount = current_salary_subquery(as_of).label("current_amount")
        effective = current_effective_date_subquery(as_of).label("current_effective")
        stmt = apply_filters(select(Employee, amount, effective), org_id, filters, as_of)

        if sort == "current_salary":
            order_col = amount
        else:
            order_col = getattr(Employee, sort)
        order = order_col.desc() if descending else order_col.asc()
        # Tie-break on id so paging is stable.
        stmt = stmt.order_by(order, Employee.id.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        return [
            EmployeeRow(employee=emp, current_amount_minor=amt, current_effective_date=eff)
            for emp, amt, eff in self.session.execute(stmt)
        ]
