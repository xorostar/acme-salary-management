from datetime import date
from decimal import Decimal

import pytest

from app.domain.errors import ValidationError
from app.domain.payroll import PayrollInput, Period, build_lines, validate_period

TODAY = date(2025, 6, 15)


def person(currency="USD", annual=12_000_000, n=1) -> PayrollInput:
    return PayrollInput(n, f"E{n}", "Ada Lovelace", "US", "Engineering", currency, annual)


class TestPeriod:
    def test_bounds_handle_february_in_leap_year(self):
        assert Period(2024, 2).end == date(2024, 2, 29)
        assert Period(2025, 2).end == date(2025, 2, 28)
        assert Period(2025, 12).start == date(2025, 12, 1)

    def test_current_and_next_month_are_allowed(self):
        assert validate_period(2025, 6, TODAY) == Period(2025, 6)
        assert validate_period(2025, 7, TODAY) == Period(2025, 7)
        assert validate_period(2020, 1, TODAY) == Period(2020, 1)

    def test_two_months_ahead_is_rejected(self):
        with pytest.raises(ValidationError) as exc:
            validate_period(2025, 8, TODAY)
        assert exc.value.errors[0].field == "month"

    def test_next_month_across_year_end(self):
        assert validate_period(2026, 1, date(2025, 12, 31)) == Period(2026, 1)

    @pytest.mark.parametrize("year,month,field", [(2025, 13, "month"), (2025, 0, "month"),
                                                  (1999, 5, "year")])  # fmt: skip
    def test_invalid_values(self, year, month, field):
        with pytest.raises(ValidationError) as exc:
            validate_period(year, month, TODAY)
        assert exc.value.errors[0].field == field


class TestBuildLines:
    def test_monthly_is_one_twelfth_rounded_half_up(self):
        # 100,000.06 / 12 = 8,333.338333 -> 8,333.34
        (line,) = build_lines([person(annual=10_000_006)], {"USD": Decimal("1")})
        assert line.amount_minor == 833_334
        assert line.amount_usd_minor == 833_334
        assert line.rate_to_usd == "1"

    def test_converts_monthly_amount_to_usd(self):
        # JPY 12,000,000 / 12 = 1,000,000 JPY * 0.0067 = USD 6,700.00
        (line,) = build_lines([person("JPY", 12_000_000)], {"JPY": Decimal("0.0067")})
        assert line.amount_minor == 1_000_000
        assert line.amount_usd_minor == 670_000
        assert line.rate_to_usd == "0.0067"

    def test_missing_rate_refuses_the_whole_run(self):
        with pytest.raises(ValidationError) as exc:
            build_lines([person("USD"), person("BRL", n=2)], {"USD": Decimal("1")})
        assert "BRL" in exc.value.errors[0].message

    def test_empty_population_gives_no_lines(self):
        assert build_lines([], {}) == []
