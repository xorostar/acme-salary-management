from decimal import Decimal

import pytest

from app.domain.money import (
    convert_minor,
    exponent,
    format_money,
    monthly_from_annual,
    to_major,
    to_minor,
)


class TestExponent:
    def test_two_decimal_currencies(self):
        assert exponent("USD") == 2
        assert exponent("INR") == 2

    def test_zero_decimal_currency(self):
        assert exponent("JPY") == 0

    def test_unsupported_currency_raises(self):
        with pytest.raises(ValueError, match="Unsupported currency"):
            exponent("XXX")


class TestToMinor:
    @pytest.mark.parametrize(
        "amount,currency,expected",
        [
            ("55000.50", "USD", 5500050),
            ("55000", "USD", 5500000),
            (55000, "USD", 5500000),
            (Decimal("0.01"), "GBP", 1),
            ("4500000", "JPY", 4500000),
            (" 1200.00 ", "EUR", 120000),
        ],
    )
    def test_parses_major_amounts(self, amount, currency, expected):
        assert to_minor(amount, currency) == expected

    def test_rejects_too_many_decimals(self):
        with pytest.raises(ValueError, match="at most 2 decimal places"):
            to_minor("10.005", "USD")

    def test_rejects_fractional_yen(self):
        with pytest.raises(ValueError, match="at most 0 decimal places"):
            to_minor("100.5", "JPY")

    @pytest.mark.parametrize("bad", ["abc", "", "NaN", "Infinity", "1,000"])
    def test_rejects_garbage(self, bad):
        with pytest.raises(ValueError):
            to_minor(bad, "USD")


class TestToMajor:
    def test_round_trip(self):
        assert to_major(5500050, "USD") == Decimal("55000.50")
        assert to_major(4500000, "JPY") == Decimal("4500000")

    def test_major_has_currency_precision(self):
        assert str(to_major(100, "USD")) == "1.00"


class TestConvert:
    def test_gbp_to_usd(self):
        # 50,000.00 GBP at 1.27 = 63,500.00 USD
        assert convert_minor(5000000, "GBP", "USD", Decimal("1.27")) == 6350000

    def test_jpy_to_usd_handles_exponent_change(self):
        # 6,000,000 JPY at 0.0067 = 40,200.00 USD
        assert convert_minor(6000000, "JPY", "USD", Decimal("0.0067")) == 4020000

    def test_usd_to_jpy_rounds_to_whole_yen(self):
        # 100.00 USD at 149.37 = 14,937 JPY
        assert convert_minor(10000, "USD", "JPY", Decimal("149.37")) == 14937

    def test_rounds_half_up_once_at_the_end(self):
        # 1.005 USD-equivalent -> 1.01, not 1.00 (banker's rounding would give 1.00)
        assert convert_minor(1005, "EUR", "USD", Decimal("1")) == 1005
        assert convert_minor(100, "EUR", "USD", Decimal("1.005")) == 101

    def test_same_currency_identity(self):
        assert convert_minor(123456, "USD", "USD", Decimal("1")) == 123456

    def test_rejects_non_positive_rate(self):
        with pytest.raises(ValueError):
            convert_minor(100, "USD", "GBP", Decimal("0"))


class TestMonthly:
    def test_exact_division(self):
        assert monthly_from_annual(1200000) == 100000

    def test_rounds_half_up(self):
        # 100,000.07 / 12 = 8,333.339... -> 8,333.34
        assert monthly_from_annual(10000007) == 833334
        # 6 / 12 = 0.5 -> rounds up to 1
        assert monthly_from_annual(6) == 1


class TestFormat:
    def test_two_decimals_with_grouping(self):
        assert format_money(5500050, "USD") == "USD 55,000.50"

    def test_zero_decimals(self):
        assert format_money(4500000, "JPY") == "JPY 4,500,000"
