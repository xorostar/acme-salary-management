"""Money arithmetic on integer minor units. Floats are never used.

See ADR 002. Every function takes and returns integers for amounts; the only
non-integer type is Decimal for exchange rates and user-entered major amounts.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Minor-unit exponent per ISO 4217 code for the currencies ACME pays in.
CURRENCY_EXPONENTS: dict[str, int] = {
    "USD": 2,
    "GBP": 2,
    "EUR": 2,
    "INR": 2,
    "JPY": 0,
    "CAD": 2,
    "AUD": 2,
    "SGD": 2,
    "BRL": 2,
}

SUPPORTED_CURRENCIES: frozenset[str] = frozenset(CURRENCY_EXPONENTS)


def exponent(currency_code: str) -> int:
    try:
        return CURRENCY_EXPONENTS[currency_code]
    except KeyError:
        raise ValueError(f"Unsupported currency: {currency_code}") from None


def _round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_minor(amount: Decimal | str | int, currency_code: str) -> int:
    """Parse a major-unit amount ("55000.50") into minor units (5500050).

    Rejects more decimal places than the currency allows, so "100.5" JPY is an
    error rather than a silent truncation.
    """
    exp = exponent(currency_code)
    try:
        major = Decimal(str(amount).strip())
    except InvalidOperation:
        raise ValueError(f"Not a valid amount: {amount!r}") from None
    if not major.is_finite():
        raise ValueError(f"Not a valid amount: {amount!r}")
    scaled = major * (Decimal(10) ** exp)
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{currency_code} allows at most {exp} decimal places")
    return int(scaled)


def to_major(amount_minor: int, currency_code: str) -> Decimal:
    exp = exponent(currency_code)
    return (Decimal(amount_minor) / (Decimal(10) ** exp)).quantize(Decimal(10) ** -exp)


def convert_minor(amount_minor: int, from_currency: str, to_currency: str, rate: Decimal) -> int:
    """Convert minor units between currencies using `rate` (1 from = rate to).

    Rounds half-up once, to the target currency's exponent, after the full
    Decimal computation.
    """
    if rate <= 0:
        raise ValueError("Exchange rate must be positive")
    major = Decimal(amount_minor) / (Decimal(10) ** exponent(from_currency))
    target_major = major * rate
    return _round_half_up(target_major * (Decimal(10) ** exponent(to_currency)))


@dataclass(frozen=True)
class RateConverter:
    """Exact conversion at one rate, precomputed for converting many amounts.

    Same result as `convert_minor` (round half-up, away from zero), but in
    integer arithmetic: the rate becomes an exact fraction once, so each
    conversion is a multiply and a floor-divide instead of several Decimal
    operations. Used where 10,000 salaries are converted per request.
    """

    numerator: int
    denominator: int

    @classmethod
    def build(cls, from_currency: str, to_currency: str, rate: Decimal) -> "RateConverter":
        if rate <= 0:
            raise ValueError("Exchange rate must be positive")
        num, den = rate.as_integer_ratio()
        return cls(num * 10 ** exponent(to_currency), den * 10 ** exponent(from_currency))

    def __call__(self, amount_minor: int) -> int:
        # round_half_up(q / d) == floor((2q + d) / 2d) for q >= 0
        q = abs(amount_minor) * self.numerator
        rounded = (2 * q + self.denominator) // (2 * self.denominator)
        return rounded if amount_minor >= 0 else -rounded


def usd_sort_factor(currency_code: str, rate_to_usd: Decimal) -> float:
    """Multiplier from one minor unit of `currency_code` to US cents.

    For ORDERING only (e.g. "highest paid first" across currencies), where a
    float is fine because no amount is ever shown or stored from it.
    """
    return float(rate_to_usd) * 10 ** (2 - exponent(currency_code))


def monthly_from_annual(annual_minor: int) -> int:
    """One twelfth of an annual amount, rounded half-up to a whole minor unit."""
    return _round_half_up(Decimal(annual_minor) / Decimal(12))


def format_money(amount_minor: int, currency_code: str) -> str:
    exp = exponent(currency_code)
    major = to_major(amount_minor, currency_code)
    return f"{currency_code} {major:,.{exp}f}"
