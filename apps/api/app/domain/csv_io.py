"""CSV import parsing/validation and export formatting. Pure, no database.

Import is all-or-nothing: every row is validated, every problem is reported
with its row number, and nothing is written unless the whole file is clean.
Uniqueness against existing employees needs a query, so the service passes
those sets in.
"""

import csv
import io
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.domain.employee import EmployeeInput, validate_employee
from app.domain.errors import ValidationError
from app.domain.money import to_minor
from app.domain.salary import validate_salary_event

IMPORT_COLUMNS: tuple[str, ...] = (
    "employee_number",
    "first_name",
    "last_name",
    "email",
    "country_code",
    "currency_code",
    "department",
    "job_title",
    "level",
    "hire_date",
    "annual_salary",
)

EXPORT_COLUMNS: tuple[str, ...] = (
    *IMPORT_COLUMNS[:-1],
    "termination_date",
    "status",
    "annual_salary",
    "salary_effective_date",
)

MAX_IMPORT_ROWS = 20_000
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


@dataclass(frozen=True)
class RowError:
    row: int  # 1-based data row number as shown in a spreadsheet (header is row 1)
    field: str
    message: str


@dataclass(frozen=True)
class ImportRow:
    employee: EmployeeInput
    annual_amount_minor: int


@dataclass(frozen=True)
class ParsedImport:
    """`rows` is empty whenever `errors` is not, so a caller cannot import a
    partially valid file by accident."""

    rows: list[ImportRow]
    errors: list[RowError]
    total_rows: int = 0


def _parse_date(value: str) -> date:
    return date.fromisoformat(value.strip())


def parse_import(
    text: str,
    *,
    existing_numbers: set[str] | None = None,
    existing_emails: set[str] | None = None,
) -> ParsedImport:
    """Validate a CSV file of new hires. Returns valid rows and every error."""
    existing_numbers = existing_numbers or set()
    existing_emails = existing_emails or set()
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in IMPORT_COLUMNS if c not in header]
    if missing:
        return ParsedImport([], [RowError(1, "header", f"missing columns: {', '.join(missing)}")])
    reader.fieldnames = header

    rows: list[ImportRow] = []
    errors: list[RowError] = []
    seen_numbers: dict[str, int] = {}
    seen_emails: dict[str, int] = {}
    total = 0

    for line_no, raw in enumerate(reader, start=2):
        if line_no - 1 > MAX_IMPORT_ROWS:
            errors.append(RowError(line_no, "file", f"more than {MAX_IMPORT_ROWS} rows"))
            break
        values = {k: (v or "").strip() for k, v in raw.items() if k is not None}
        if not any(values.values()):
            continue  # skip blank lines
        total += 1
        row_errors: list[RowError] = []

        try:
            hire = _parse_date(values["hire_date"])
        except ValueError:
            row_errors.append(RowError(line_no, "hire_date", "must be a date like 2024-01-31"))
            hire = None

        # Validate the other fields even when the date is bad, so the user sees
        # every problem in one pass. A placeholder date stands in for checking.
        employee = None
        try:
            fields = {c: values[c] for c in IMPORT_COLUMNS[:-2]}
            checked = validate_employee(EmployeeInput(**fields, hire_date=hire or date.min))
            employee = checked if hire is not None else None
        except ValidationError as exc:
            row_errors.extend(RowError(line_no, e.field, e.message) for e in exc.errors)

        amount = None
        if employee is not None:
            try:
                amount = to_minor(values["annual_salary"], employee.currency_code)
                validate_salary_event(
                    hire_date=employee.hire_date,
                    employee_currency=employee.currency_code,
                    existing_effective_dates=[],
                    annual_amount_minor=amount,
                    currency_code=employee.currency_code,
                    effective_date=employee.hire_date,
                    reason="Hire",
                )
            except ValueError as exc:
                row_errors.append(RowError(line_no, "annual_salary", str(exc)))
            except ValidationError as exc:
                row_errors.extend(RowError(line_no, "annual_salary", e.message)
                                  for e in exc.errors)  # fmt: skip

            number, email = employee.employee_number, employee.email
            if number in existing_numbers:
                row_errors.append(RowError(line_no, "employee_number", "already exists"))
            elif number in seen_numbers:
                row_errors.append(RowError(line_no, "employee_number",
                                           f"duplicate of row {seen_numbers[number]}"))  # fmt: skip
            if email in existing_emails:
                row_errors.append(RowError(line_no, "email", "already exists"))
            elif email in seen_emails:
                row_errors.append(RowError(line_no, "email",
                                           f"duplicate of row {seen_emails[email]}"))  # fmt: skip
            seen_numbers.setdefault(number, line_no)
            seen_emails.setdefault(email, line_no)

        if row_errors:
            errors.extend(row_errors)
        elif employee is not None and amount is not None:
            rows.append(ImportRow(employee, amount))

    if total == 0 and not errors:
        errors.append(RowError(2, "file", "contains no data rows"))
    return ParsedImport([] if errors else rows, errors, total)


def import_keys(text: str) -> tuple[list[str], list[str]]:
    """Employee numbers and emails mentioned in a file, normalized, so the
    service can look up which already exist before validating."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    numbers, emails = [], []
    for raw in reader:
        row = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
        if row.get("employee_number"):
            numbers.append(row["employee_number"].upper())
        if row.get("email"):
            emails.append(row["email"].lower())
    return numbers, emails


def safe_cell(value: object) -> str:
    """Neutralize spreadsheet formula injection: a cell that starts with = + - @
    is prefixed with an apostrophe so Excel shows it as text."""
    text = "" if value is None else str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def write_csv(rows: Iterable[Iterable[object]], header: Iterable[str]) -> Iterable[str]:
    """Yield CSV text in chunks so large exports stream instead of buffering."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(list(header))
    for i, row in enumerate(rows, start=1):
        writer.writerow([safe_cell(v) for v in row])
        if i % 500 == 0:
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()
    yield buffer.getvalue()
