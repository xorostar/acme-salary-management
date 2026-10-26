"""Analytics math checked against values worked out by hand."""

from decimal import Decimal

import pytest

from app.domain.analytics import (
    PayRecord,
    convert_to_usd,
    median_matrix,
    summarize_by,
    usd_histogram,
)

RATES = {"USD": Decimal("1"), "GBP": Decimal("1.25"), "JPY": Decimal("0.0067")}


def rec(country, currency, amount, dept="Engineering", level="L3") -> PayRecord:
    return PayRecord(country, dept, level, currency, amount)


def test_conversion_uses_currency_exponent():
    # GBP 80,000.00 * 1.25 = USD 100,000.00 ; JPY 10,000,000 * 0.0067 = USD 67,000.00
    conv = convert_to_usd([rec("GB", "GBP", 8_000_000), rec("JP", "JPY", 10_000_000)], RATES)
    assert [c.usd_minor for c in conv.converted] == [10_000_000, 6_700_000]
    assert conv.missing_currencies == frozenset()


def test_records_without_a_rate_are_excluded_and_reported():
    conv = convert_to_usd([rec("US", "USD", 100), rec("BR", "BRL", 100)], RATES)
    assert len(conv.converted) == 1
    assert conv.missing_currencies == {"BRL"}


def test_summarize_by_country_gives_usd_and_local_figures():
    records = [
        rec("US", "USD", 10_000_000),
        rec("US", "USD", 12_000_000),
        rec("US", "USD", 20_000_000),
        rec("GB", "GBP", 8_000_000),
    ]
    groups = summarize_by(convert_to_usd(records, RATES).converted, "country_code")

    us, gb = groups  # largest headcount first
    assert us.key == "US"
    assert us.usd.count == 3
    assert us.usd.p50 == 12_000_000
    assert us.usd.mean == 14_000_000
    assert us.usd.total == 42_000_000
    assert gb.key == "GB"
    assert gb.local_currency == "GBP"
    assert gb.local.p50 == 8_000_000
    assert gb.usd.p50 == 10_000_000


def test_mixed_currency_group_has_no_local_summary():
    records = [rec("US", "USD", 100, dept="Legal"), rec("GB", "GBP", 100, dept="Legal")]
    (legal,) = summarize_by(convert_to_usd(records, RATES).converted, "department")
    assert legal.local_currency is None
    assert legal.local is None
    assert legal.usd.count == 2


def test_groups_with_equal_headcount_sort_by_key():
    records = [rec("US", "USD", 1, level="L5"), rec("US", "USD", 1, level="L1")]
    groups = summarize_by(convert_to_usd(records, RATES).converted, "level")
    assert [g.key for g in groups] == ["L1", "L5"]


def test_unknown_dimension_is_rejected():
    with pytest.raises(ValueError):
        summarize_by([], "salary")  # type: ignore[arg-type]


def test_median_matrix_level_by_country():
    records = [
        rec("US", "USD", 10_000_000, level="L3"),
        rec("US", "USD", 14_000_000, level="L3"),
        rec("GB", "GBP", 8_000_000, level="L3"),
        rec("US", "USD", 20_000_000, level="L5"),
    ]
    cells = median_matrix(convert_to_usd(records, RATES).converted, "level", "country_code")

    assert [(c.row, c.col, c.count, c.median_usd_minor) for c in cells] == [
        ("L3", "GB", 1, 10_000_000),
        ("L3", "US", 2, 12_000_000),
        ("L5", "US", 1, 20_000_000),
    ]


def test_matrix_needs_two_different_dimensions():
    with pytest.raises(ValueError):
        median_matrix([], "level", "level")


def test_histogram_is_in_usd():
    records = [rec("US", "USD", 100), rec("US", "USD", 200), rec("US", "USD", 300)]
    buckets = usd_histogram(convert_to_usd(records, RATES).converted, bins=2)
    assert [b.count for b in buckets] == [1, 2]
    assert buckets[0].start == 100
