"""CSV import of new hires and export of the directory."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.domain.csv_io import EXPORT_COLUMNS, RowError, import_keys, parse_import, write_csv
from app.domain.employee import is_active
from app.domain.money import to_major
from app.models import Employee, SalaryEvent
from app.repositories.employees import EmployeeFilters, EmployeeRepository, SortField
from app.services.auth import CurrentUser
from app.services.employees import usd_sort_factors

HIRE_REASON = "Hire"


@dataclass(frozen=True)
class ImportResult:
    total_rows: int
    imported: int
    dry_run: bool
    errors: list[RowError]

    @property
    def ok(self) -> bool:
        return not self.errors


class CsvTransferService:
    def __init__(self, session: Session, *, today: date, user: CurrentUser):
        self.session = session
        self.today = today
        self.user = user
        self.employees = EmployeeRepository(session)

    def import_employees(self, text: str, *, dry_run: bool) -> ImportResult:
        org = self.user.organization_id
        numbers, emails = import_keys(text)
        parsed = parse_import(
            text,
            existing_numbers=self.employees.existing_numbers(org, numbers),
            existing_emails=self.employees.existing_emails(org, emails),
        )
        if parsed.errors or dry_run:
            imported = 0 if parsed.errors else len(parsed.rows)
            return ImportResult(parsed.total_rows, imported, dry_run, parsed.errors)

        employee_rows = [{"organization_id": org, "version": 1, **r.employee.__dict__}
                         for r in parsed.rows]  # fmt: skip
        ids = list(
            self.session.scalars(
                insert(Employee).returning(Employee.id, sort_by_parameter_order=True),
                employee_rows,
            )
        )
        self.session.execute(
            insert(SalaryEvent),
            [
                {
                    "organization_id": org,
                    "employee_id": emp_id,
                    "annual_amount_minor": r.annual_amount_minor,
                    "currency_code": r.employee.currency_code,
                    "effective_date": r.employee.hire_date,
                    "reason": HIRE_REASON,
                    "created_by_user_id": self.user.id,
                }
                for emp_id, r in zip(ids, parsed.rows, strict=True)
            ],
        )
        self.session.commit()
        return ImportResult(parsed.total_rows, len(ids), False, [])

    def export_csv(
        self, filters: EmployeeFilters, *, sort: SortField, descending: bool
    ) -> Iterator[str]:
        rows = self.employees.export_rows(
            self.user.organization_id,
            filters,
            self.today,
            sort=sort,
            descending=descending,
            usd_factors=usd_sort_factors(self.session, self.today),
        )

        def cells():
            for r in rows:
                e = r.employee
                yield [
                    e.employee_number, e.first_name, e.last_name, e.email, e.country_code,
                    e.currency_code, e.department, e.job_title, e.level, e.hire_date.isoformat(),
                    e.termination_date.isoformat() if e.termination_date else "",
                    "active" if is_active(e.termination_date, self.today) else "terminated",
                    to_major(r.current_amount_minor, e.currency_code)
                    if r.current_amount_minor is not None else "",
                    r.current_effective_date.isoformat() if r.current_effective_date else "",
                ]  # fmt: skip

        return write_csv(cells(), EXPORT_COLUMNS)
