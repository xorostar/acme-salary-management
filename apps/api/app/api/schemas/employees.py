from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.money import to_major
from app.domain.reference import COUNTRIES
from app.models import Employee, SalaryEvent


class SalaryOut(BaseModel):
    annual_amount_minor: int
    annual_salary: str
    currency_code: str
    effective_date: date

    @classmethod
    def build(cls, amount_minor: int, currency_code: str, effective_date: date) -> "SalaryOut":
        return cls(
            annual_amount_minor=amount_minor,
            annual_salary=str(to_major(amount_minor, currency_code)),
            currency_code=currency_code,
            effective_date=effective_date,
        )


class SalaryEventOut(SalaryOut):
    id: int
    reason: str
    created_by: str | None
    created_at: datetime

    @classmethod
    def from_model(cls, e: SalaryEvent, created_by: str | None) -> "SalaryEventOut":
        return cls(
            id=e.id,
            annual_amount_minor=e.annual_amount_minor,
            annual_salary=str(to_major(e.annual_amount_minor, e.currency_code)),
            currency_code=e.currency_code,
            effective_date=e.effective_date,
            reason=e.reason,
            created_by=created_by,
            created_at=e.created_at,
        )


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_number: str
    first_name: str
    last_name: str
    email: str
    country_code: str
    country_name: str
    currency_code: str
    department: str
    job_title: str
    level: str
    hire_date: date
    termination_date: date | None
    is_active: bool
    version: int
    current_salary: SalaryOut | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(
        cls,
        emp: Employee,
        *,
        is_active: bool,
        current_amount_minor: int | None,
        current_effective_date: date | None,
    ) -> "EmployeeOut":
        current = None
        if current_amount_minor is not None and current_effective_date is not None:
            current = SalaryOut.build(
                current_amount_minor, emp.currency_code, current_effective_date
            )
        country = COUNTRIES.get(emp.country_code)
        return cls(
            id=emp.id,
            employee_number=emp.employee_number,
            first_name=emp.first_name,
            last_name=emp.last_name,
            email=emp.email,
            country_code=emp.country_code,
            country_name=country.name if country else emp.country_code,
            currency_code=emp.currency_code,
            department=emp.department,
            job_title=emp.job_title,
            level=emp.level,
            hire_date=emp.hire_date,
            termination_date=emp.termination_date,
            is_active=is_active,
            version=emp.version,
            current_salary=current,
            created_at=emp.created_at,
            updated_at=emp.updated_at,
        )


class EmployeeDetailOut(EmployeeOut):
    salary_history: list[SalaryEventOut]


class EmployeeListOut(BaseModel):
    items: list[EmployeeOut]
    page: int
    page_size: int
    total: int


class EmployeeBase(BaseModel):
    employee_number: str = Field(max_length=20)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str = Field(max_length=254)
    country_code: str = Field(max_length=2)
    currency_code: str = Field(max_length=3)
    department: str = Field(max_length=100)
    job_title: str = Field(max_length=150)
    level: str = Field(max_length=10)
    hire_date: date


class SalaryChangeIn(BaseModel):
    annual_salary: str = Field(max_length=32, description="Major units, e.g. '85000.00'")
    effective_date: date
    reason: str = Field(max_length=200)


class EmployeeCreateIn(EmployeeBase):
    annual_salary: str = Field(max_length=32, description="Starting salary in major units")


class EmployeeUpdateIn(EmployeeBase):
    version: int
    salary_change: SalaryChangeIn | None = None


class TerminateIn(BaseModel):
    termination_date: date
    version: int


class ReactivateIn(BaseModel):
    version: int


SortParam = Literal[
    "last_name",
    "employee_number",
    "hire_date",
    "department",
    "country_code",
    "level",
    "current_salary",
]
StatusParam = Literal["active", "terminated", "all"]
