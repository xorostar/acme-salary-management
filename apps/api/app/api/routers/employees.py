from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUserDep, SessionDep, TodayDep, require_role
from app.api.schemas.employees import (
    EmployeeCreateIn,
    EmployeeDetailOut,
    EmployeeListOut,
    EmployeeOut,
    EmployeeUpdateIn,
    ReactivateIn,
    SalaryChangeIn,
    SalaryEventOut,
    SortParam,
    StatusParam,
    TerminateIn,
)
from app.domain.employee import EmployeeInput, is_active
from app.domain.reference import ROLE_ADMIN
from app.repositories.employees import EmployeeFilters
from app.services.auth import CurrentUser
from app.services.employees import EmployeeService, SalaryChangeInput

router = APIRouter(prefix="/employees", tags=["employees"])

AdminDep = Annotated[CurrentUser, Depends(require_role(ROLE_ADMIN))]


def _service(session: SessionDep, today: TodayDep, user: CurrentUser) -> EmployeeService:
    return EmployeeService(session, today=today, user=user)


def _to_input(body: EmployeeCreateIn | EmployeeUpdateIn) -> EmployeeInput:
    return EmployeeInput(
        employee_number=body.employee_number,
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        country_code=body.country_code,
        currency_code=body.currency_code,
        department=body.department,
        job_title=body.job_title,
        level=body.level,
        hire_date=body.hire_date,
    )


def _to_change(body: SalaryChangeIn) -> SalaryChangeInput:
    return SalaryChangeInput(
        annual_salary=body.annual_salary, effective_date=body.effective_date, reason=body.reason
    )


def _detail(service: EmployeeService, employee_id: int) -> EmployeeDetailOut:
    emp, events = service.get(employee_id)
    current = service.current_salary_point(events)
    names = service.recorder_names(events)
    base = EmployeeOut.from_model(
        emp,
        is_active=is_active(emp.termination_date, service.today),
        current_amount_minor=current.annual_amount_minor if current else None,
        current_effective_date=current.effective_date if current else None,
    )
    history = [SalaryEventOut.from_model(e, names.get(e.created_by_user_id)) for e in events]
    return EmployeeDetailOut(**base.model_dump(), salary_history=history)


@router.get("", response_model=EmployeeListOut)
def list_employees(
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
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
) -> EmployeeListOut:
    service = _service(session, today, user)
    filters = EmployeeFilters(
        q=q, country_code=country_code, department=department, level=level, status=status_filter
    )
    rows, total = service.search(
        filters, page=page, page_size=page_size, sort=sort, descending=(order == "desc")
    )
    items = [
        EmployeeOut.from_model(
            r.employee,
            is_active=is_active(r.employee.termination_date, today),
            current_amount_minor=r.current_amount_minor,
            current_effective_date=r.current_effective_date,
        )
        for r in rows
    ]
    return EmployeeListOut(items=items, page=page, page_size=page_size, total=total)


@router.get("/{employee_id}", response_model=EmployeeDetailOut)
def get_employee(
    employee_id: int, session: SessionDep, today: TodayDep, user: CurrentUserDep
) -> EmployeeDetailOut:
    return _detail(_service(session, today, user), employee_id)


@router.post("", response_model=EmployeeDetailOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    body: EmployeeCreateIn, session: SessionDep, today: TodayDep, user: AdminDep
) -> EmployeeDetailOut:
    service = _service(session, today, user)
    emp = service.create(_to_input(body), body.annual_salary)
    return _detail(service, emp.id)


@router.put("/{employee_id}", response_model=EmployeeDetailOut)
def update_employee(
    employee_id: int,
    body: EmployeeUpdateIn,
    session: SessionDep,
    today: TodayDep,
    user: AdminDep,
) -> EmployeeDetailOut:
    service = _service(session, today, user)
    service.update(
        employee_id,
        _to_input(body),
        expected_version=body.version,
        salary_change=_to_change(body.salary_change) if body.salary_change else None,
    )
    return _detail(service, employee_id)


@router.post("/{employee_id}/salary-events", response_model=EmployeeDetailOut, status_code=201)
def add_salary_event(
    employee_id: int,
    body: SalaryChangeIn,
    session: SessionDep,
    today: TodayDep,
    user: AdminDep,
) -> EmployeeDetailOut:
    service = _service(session, today, user)
    service.add_salary_event(employee_id, _to_change(body))
    return _detail(service, employee_id)


@router.post("/{employee_id}/terminate", response_model=EmployeeDetailOut)
def terminate_employee(
    employee_id: int, body: TerminateIn, session: SessionDep, today: TodayDep, user: AdminDep
) -> EmployeeDetailOut:
    service = _service(session, today, user)
    service.terminate(employee_id, body.termination_date, expected_version=body.version)
    return _detail(service, employee_id)


@router.post("/{employee_id}/reactivate", response_model=EmployeeDetailOut)
def reactivate_employee(
    employee_id: int, body: ReactivateIn, session: SessionDep, today: TodayDep, user: AdminDep
) -> EmployeeDetailOut:
    service = _service(session, today, user)
    service.reactivate(employee_id, expected_version=body.version)
    return _detail(service, employee_id)
