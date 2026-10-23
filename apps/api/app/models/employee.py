from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Employee(Base):
    """An employee record. Salary is NOT stored here; see SalaryEvent.

    Status is derived: an employee is active on a given date when
    termination_date is NULL or later than that date.
    """

    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("organization_id", "employee_number", name="uq_employees_org_number"),
        UniqueConstraint("organization_id", "email", name="uq_employees_org_email"),
        Index("ix_employees_org_country", "organization_id", "country_code"),
        Index("ix_employees_org_department", "organization_id", "department"),
        Index("ix_employees_org_level", "organization_id", "level"),
        Index("ix_employees_org_name", "organization_id", "last_name", "first_name"),
        Index("ix_employees_org_termination", "organization_id", "termination_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    employee_number: Mapped[str] = mapped_column(String(20), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    salary_events: Mapped[list["SalaryEvent"]] = relationship(  # noqa: F821
        back_populates="employee",
        order_by="desc(SalaryEvent.effective_date)",
        cascade="all, delete-orphan",
    )
