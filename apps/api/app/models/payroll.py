from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PayrollRun(Base):
    """A frozen monthly snapshot of what each active employee is owed."""

    __tablename__ = "payroll_runs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "period_year", "period_month", name="uq_payroll_runs_org_period"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    period_year: Mapped[int] = mapped_column(nullable=False)
    period_month: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    employee_count: Mapped[int] = mapped_column(nullable=False, default=0)
    total_usd_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    lines: Mapped[list["PayrollLine"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class PayrollLine(Base):
    """One employee's pay for one run. Values are copied at run time and never change."""

    __tablename__ = "payroll_lines"
    __table_args__ = (
        UniqueConstraint("payroll_run_id", "employee_id", name="uq_payroll_lines_run_employee"),
        Index("ix_payroll_lines_run_country", "payroll_run_id", "country_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payroll_run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    employee_number: Mapped[str] = mapped_column(String(20), nullable=False)
    employee_name: Mapped[str] = mapped_column(String(201), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    annual_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_usd_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rate_to_usd: Mapped[str] = mapped_column(String(32), nullable=False)

    run: Mapped[PayrollRun] = relationship(back_populates="lines")
