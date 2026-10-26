from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ExchangeRate


class ExchangeRateRepository:
    def __init__(self, session: Session):
        self.session = session

    def rates_as_of(self, as_of: date) -> dict[str, Decimal]:
        """Latest rate to USD per currency with effective_date <= as_of."""
        latest = (
            select(
                ExchangeRate.currency_code,
                func.max(ExchangeRate.effective_date).label("effective_date"),
            )
            .where(ExchangeRate.effective_date <= as_of)
            .group_by(ExchangeRate.currency_code)
            .subquery()
        )
        stmt = select(ExchangeRate.currency_code, ExchangeRate.rate_to_usd).join(
            latest,
            (ExchangeRate.currency_code == latest.c.currency_code)
            & (ExchangeRate.effective_date == latest.c.effective_date),
        )
        rates = {code: Decimal(rate) for code, rate in self.session.execute(stmt)}
        rates.setdefault("USD", Decimal("1"))
        return rates

    def add(self, rate: ExchangeRate) -> ExchangeRate:
        self.session.add(rate)
        self.session.flush()
        return rate
