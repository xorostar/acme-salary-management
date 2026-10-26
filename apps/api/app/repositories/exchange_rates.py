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
        rates = {code: Decimal(rate) for code, rate, _ in self.rates_in_force(as_of)}
        rates.setdefault("USD", Decimal("1"))
        return rates

    def rates_in_force(self, as_of: date) -> list[tuple[str, str, date]]:
        """(currency, rate_to_usd, effective_date) for the rate in force on as_of."""
        latest = (
            select(
                ExchangeRate.currency_code,
                func.max(ExchangeRate.effective_date).label("effective_date"),
            )
            .where(ExchangeRate.effective_date <= as_of)
            .group_by(ExchangeRate.currency_code)
            .subquery()
        )
        stmt = (
            select(
                ExchangeRate.currency_code, ExchangeRate.rate_to_usd, ExchangeRate.effective_date
            )
            .join(
                latest,
                (ExchangeRate.currency_code == latest.c.currency_code)
                & (ExchangeRate.effective_date == latest.c.effective_date),
            )
            .order_by(ExchangeRate.currency_code)
        )
        return [(code, rate, eff) for code, rate, eff in self.session.execute(stmt)]

    def add(self, rate: ExchangeRate) -> ExchangeRate:
        self.session.add(rate)
        self.session.flush()
        return rate
