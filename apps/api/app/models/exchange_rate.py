from datetime import date

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ExchangeRate(Base):
    """Planning rate from a currency to USD, effective from a date.

    rate_to_usd is stored as a decimal string and parsed with Decimal.
    Rates are global (not per organization) because they describe the market.
    """

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("currency_code", "effective_date", name="uq_exchange_rates_ccy_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    rate_to_usd: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
