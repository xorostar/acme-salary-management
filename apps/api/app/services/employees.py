from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.employee import EmployeeInput, normalize_employee, validate_employee
from app.domain.errors import ConflictError, FieldError, NotFoundError, ValidationError
from app.domain.money import to_minor
from app.domain.salary import SalaryPoint, current_salary, validate_salary_event
from app.models import Employee, SalaryEvent, User
from app.repositories.employees import (
    EmployeeFilters,
    EmployeeRepository,
    EmployeeRow,
    SortField,
)
from app.repositories.salary_events import SalaryEventRepository
from app.services.auth import CurrentUser

MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class SalaryChangeInput:
    annual_salary: str  # major units as a decimal string, e.g. "85000.00"
    effective_date: date
    reason: str


def _parse_salary(annual_salary: str, currency_code: str, field: str = "annual_salary") -> int:
    try:
        return to_minor(annual_salary, currency_code)
    except ValueError as exc:
        raise ValidationError.single(field, str(exc)) from None


class EmployeeService:
    def __init__(self, session: Session, *, today: date, user: CurrentUser):
        self.session = session
        self.today = today
        self.user = user
        self.employees = EmployeeRepository(session)
        self.events = SalaryEventRepository(session)

    # ---- reads -------------------------------------------------------------

    def search(
        self,
        filters: EmployeeFilters,
        *,
        page: int = 1,
        page_size: int = 25,
        sort: SortField = "last_name",
        descending: bool = False,
    ) -> tuple[list[EmployeeRow], int]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
        org = self.user.organization_id
        total = self.employees.count(org, filters, self.today)
        rows = self.employees.search(
            org,
            filters,
            self.today,
            page=page,
            page_size=page_size,
            sort=sort,
            descending=descending,
        )
        return rows, total

    def get(self, employee_id: int) -> tuple[Employee, list[SalaryEvent]]:
        emp = self._require(employee_id)
        return emp, self.events.list_for_employee(emp.id)

    def current_salary_point(self, events: list[SalaryEvent]) -> SalaryPoint | None:
        return current_salary(
            (SalaryPoint(e.effective_date, e.annual_amount_minor, e.currency_code) for e in events),
            self.today,
        )

    def recorder_names(self, events: list[SalaryEvent]) -> dict[int, str]:
        """Full names of the users who recorded these events, keyed by user id."""
        ids = {e.created_by_user_id for e in events if e.created_by_user_id is not None}
        if not ids:
            return {}
        rows = self.session.execute(
            select(User.id, User.full_name).where(
                User.id.in_(ids), User.organization_id == self.user.organization_id
            )
        )
        return dict(rows.all())

    # ---- writes ------------------------------------------------------------

    def create(self, data: EmployeeInput, initial_salary: str) -> Employee:
        clean = self._validate_with_uniqueness(data, exclude_id=None)
        amount = _parse_salary(initial_salary, clean.currency_code)
        validate_salary_event(
            hire_date=clean.hire_date,
            employee_currency=clean.currency_code,
            existing_effective_dates=[],
            annual_amount_minor=amount,
            currency_code=clean.currency_code,
            effective_date=clean.hire_date,
            reason="Hire",
        )
        emp = Employee(organization_id=self.user.organization_id, **clean.__dict__)
        self.employees.add(emp)
        self.events.add(
            SalaryEvent(
                organization_id=emp.organization_id,
                employee_id=emp.id,
                annual_amount_minor=amount,
                currency_code=clean.currency_code,
                effective_date=clean.hire_date,
                reason="Hire",
                created_by_user_id=self.user.id,
            )
        )
        self.session.commit()
        return emp

    def update(
        self,
        employee_id: int,
        data: EmployeeInput,
        *,
        expected_version: int,
        salary_change: SalaryChangeInput | None = None,
    ) -> Employee:
        emp = self._require(employee_id)
        self._check_version(emp, expected_version)
        clean = self._validate_with_uniqueness(data, exclude_id=emp.id)

        existing_dates = self.events.effective_dates(emp.id)
        errors: list[FieldError] = []
        if existing_dates and clean.hire_date > min(existing_dates):
            errors.append(
                FieldError(
                    "hire_date",
                    f"cannot be after the first salary event ({min(existing_dates).isoformat()})",
                )
            )
        currency_changed = clean.currency_code != emp.currency_code
        if currency_changed and existing_dates and salary_change is None:
            errors.append(
                FieldError(
                    "currency_code",
                    "changing currency requires a salary_change in the new currency",
                )
            )
        if errors:
            raise ValidationError(errors)

        for field, value in clean.__dict__.items():
            setattr(emp, field, value)
        emp.version += 1
        self.session.flush()

        if salary_change is not None:
            self._add_event(emp, salary_change)
        self.session.commit()
        return emp

    def terminate(
        self, employee_id: int, termination_date: date, *, expected_version: int
    ) -> Employee:
        emp = self._require(employee_id)
        self._check_version(emp, expected_version)
        if termination_date < emp.hire_date:
            raise ValidationError.single("termination_date", "cannot be before hire date")
        emp.termination_date = termination_date
        emp.version += 1
        self.session.commit()
        return emp

    def reactivate(self, employee_id: int, *, expected_version: int) -> Employee:
        emp = self._require(employee_id)
        self._check_version(emp, expected_version)
        if emp.termination_date is None:
            raise ConflictError("Employee is not terminated")
        emp.termination_date = None
        emp.version += 1
        self.session.commit()
        return emp

    def add_salary_event(self, employee_id: int, change: SalaryChangeInput) -> SalaryEvent:
        emp = self._require(employee_id)
        event = self._add_event(emp, change)
        self.session.commit()
        return event

    # ---- helpers -----------------------------------------------------------

    def _require(self, employee_id: int) -> Employee:
        emp = self.employees.get(self.user.organization_id, employee_id)
        if emp is None:
            raise NotFoundError(f"Employee {employee_id} not found")
        return emp

    @staticmethod
    def _check_version(emp: Employee, expected_version: int) -> None:
        if emp.version != expected_version:
            raise ConflictError("This employee was changed by someone else. Reload and try again.")

    def _validate_with_uniqueness(
        self, data: EmployeeInput, *, exclude_id: int | None
    ) -> EmployeeInput:
        """Run domain validation and uniqueness checks, reporting both together."""
        org = self.user.organization_id
        errors: list[FieldError] = []
        try:
            clean = validate_employee(data)
        except ValidationError as exc:
            errors.extend(exc.errors)
            clean = normalize_employee(data)
        failed = {e.field for e in errors}
        if "employee_number" not in failed and self.employees.number_exists(
            org, clean.employee_number, exclude_id
        ):
            errors.append(FieldError("employee_number", "is already in use"))
        if "email" not in failed and self.employees.email_exists(org, clean.email, exclude_id):
            errors.append(FieldError("email", "is already in use"))
        if errors:
            raise ValidationError(errors)
        return clean

    def _add_event(self, emp: Employee, change: SalaryChangeInput) -> SalaryEvent:
        amount = _parse_salary(change.annual_salary, emp.currency_code)
        validate_salary_event(
            hire_date=emp.hire_date,
            employee_currency=emp.currency_code,
            existing_effective_dates=self.events.effective_dates(emp.id),
            annual_amount_minor=amount,
            currency_code=emp.currency_code,
            effective_date=change.effective_date,
            reason=change.reason,
        )
        return self.events.add(
            SalaryEvent(
                organization_id=emp.organization_id,
                employee_id=emp.id,
                annual_amount_minor=amount,
                currency_code=emp.currency_code,
                effective_date=change.effective_date,
                reason=change.reason.strip(),
                created_by_user_id=self.user.id,
            )
        )
