"""CSV import and export. Registered before the employee router so that
/employees/export.csv is not captured by /employees/{employee_id}."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.api.deps import CurrentUserDep, SessionDep, TodayDep, require_role
from app.api.schemas.employees import SortParam, StatusParam
from app.domain.csv_io import IMPORT_COLUMNS, write_csv
from app.domain.errors import ValidationError
from app.domain.reference import ROLE_ADMIN
from app.repositories.employees import EmployeeFilters
from app.services.auth import CurrentUser
from app.services.csv_transfer import CsvTransferService

router = APIRouter(prefix="/employees", tags=["csv"])

AdminDep = Annotated[CurrentUser, Depends(require_role(ROLE_ADMIN))]
# Below Vercel's 4.5 MB request-body limit, so users get this message, not a 413.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_ERRORS_RETURNED = 500  # the UI shows a table; the count tells the full story

TEMPLATE_EXAMPLE = [
    "AC90001", "Grace", "Hopper", "grace.hopper@acme.example", "US", "USD", "Engineering",
    "Staff Software Engineer", "L5", "2026-11-01", "165000.00",
]  # fmt: skip


class RowErrorOut(BaseModel):
    row: int
    field: str
    message: str


class ImportOut(BaseModel):
    total_rows: int
    imported: int
    dry_run: bool
    error_count: int
    errors: list[RowErrorOut]


def _csv_response(chunks, filename: str) -> StreamingResponse:
    return StreamingResponse(
        chunks,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export.csv", response_class=StreamingResponse)
def export_csv(
    session: SessionDep,
    today: TodayDep,
    user: CurrentUserDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    country_code: Annotated[str | None, Query(max_length=2)] = None,
    department: Annotated[str | None, Query(max_length=100)] = None,
    level: Annotated[str | None, Query(max_length=10)] = None,
    status_filter: Annotated[StatusParam, Query(alias="status")] = "active",
    sort: SortParam = "last_name",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",
):
    """The filtered directory with current salaries, as CSV. Available to viewers too."""
    filters = EmployeeFilters(q=q, country_code=country_code, department=department,
                              level=level, status=status_filter)  # fmt: skip
    chunks = CsvTransferService(session, today=today, user=user).export_csv(
        filters, sort=sort, descending=(order == "desc")
    )
    return _csv_response(chunks, f"acme-employees-{today.isoformat()}.csv")


@router.get("/import-template.csv", response_class=StreamingResponse)
def import_template(_user: CurrentUserDep):
    return _csv_response(write_csv([TEMPLATE_EXAMPLE], IMPORT_COLUMNS), "acme-import-template.csv")


@router.post("/import", response_model=ImportOut)
def import_csv(
    session: SessionDep,
    today: TodayDep,
    user: AdminDep,
    file: Annotated[UploadFile, File(description="CSV with the template's columns")],
    dry_run: bool = False,
):
    """Create new hires from a CSV. All-or-nothing: any error rejects the whole
    file with every row error listed. `dry_run=true` validates without saving."""
    # Sync handler: FastAPI runs it in a worker thread, so the blocking DB
    # work of a large import does not stall the event loop.
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValidationError.single("file", "must be at most 4 MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError.single("file", "must be UTF-8 encoded CSV") from None

    result = CsvTransferService(session, today=today, user=user).import_employees(
        text, dry_run=dry_run
    )
    body = ImportOut(
        total_rows=result.total_rows,
        imported=result.imported,
        dry_run=result.dry_run,
        error_count=len(result.errors),
        errors=[RowErrorOut(**e.__dict__) for e in result.errors[:MAX_ERRORS_RETURNED]],
    )
    return JSONResponse(status_code=200 if result.ok else 422, content=body.model_dump())
