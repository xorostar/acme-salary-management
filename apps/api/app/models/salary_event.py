from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SalaryEvent(Base):
    """Append-only record of a salary taking effect on a date. Never updated."""

    __tablename__ = "salary_events"
    __table_args__ = (
        UniqueConstraint("employee_id", "effective_date", name="uq_salary_events_employee_date"),
        CheckConstraint("annual_amount_minor > 0", name="ck_salary_events_positive"),
        Index("ix_salary_events_employee_date", "employee_id", "effective_date"),
        Index("ix_salary_events_org", "organization_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    annual_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    employee: Mapped["Employee"] = relationship(back_populates="salary_events")  # noqa: F821
