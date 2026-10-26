from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SalaryEvent


class SalaryEventRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_employee(self, employee_id: int) -> list[SalaryEvent]:
        stmt = (
            select(SalaryEvent)
            .where(SalaryEvent.employee_id == employee_id)
            .order_by(SalaryEvent.effective_date.desc(), SalaryEvent.id.desc())
        )
        return list(self.session.scalars(stmt))

    def effective_dates(self, employee_id: int) -> list[date]:
        stmt = select(SalaryEvent.effective_date).where(SalaryEvent.employee_id == employee_id)
        return list(self.session.scalars(stmt))

    def add(self, event: SalaryEvent) -> SalaryEvent:
        self.session.add(event)
        self.session.flush()
        return event
