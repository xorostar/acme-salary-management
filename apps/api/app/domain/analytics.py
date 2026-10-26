"""Compensation analytics over a population of current salaries.

Pure functions: the service fetches each active employee's salary in force on
the reference date, and everything here is arithmetic on those values.
Cross-country figures are converted to USD once per record with the planning
rate in force, then aggregated as integers (ADR 002, ADR 006).
"""

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.domain.money import RateConverter
from app.domain.stats import Bucket, Summary, histogram, summarize

Dimension = Literal["country_code", "department", "level"]
DIMENSIONS: tuple[Dimension, ...] = ("country_code", "department", "level")


@dataclass(frozen=True)
class PayRecord:
    """One active employee's current annual salary, in local currency."""

    country_code: str
    department: str
    level: str
    currency_code: str
    annual_amount_minor: int


@dataclass(frozen=True)
class ConvertedRecord:
    record: PayRecord
    usd_minor: int


@dataclass(frozen=True)
class Conversion:
    converted: list[ConvertedRecord]
    missing_currencies: frozenset[str]


def convert_to_usd(records: Iterable[PayRecord], rates: dict[str, Decimal]) -> Conversion:
    """Convert every record whose currency has a rate. Records without a rate
    are excluded and their currencies reported, never silently guessed."""
    converters = {code: RateConverter.build(code, "USD", rate) for code, rate in rates.items()}
    converted: list[ConvertedRecord] = []
    missing: set[str] = set()
    for r in records:
        to_usd = converters.get(r.currency_code)
        if to_usd is None:
            missing.add(r.currency_code)
            continue
        converted.append(ConvertedRecord(r, to_usd(r.annual_amount_minor)))
    return Conversion(converted, frozenset(missing))


@dataclass(frozen=True)
class GroupSummary:
    key: str
    usd: Summary
    # Local-currency summary, only when every member shares one currency
    # (always true when grouping by country).
    local_currency: str | None
    local: Summary | None


def _key_fn(dimension: Dimension) -> Callable[[PayRecord], str]:
    if dimension not in DIMENSIONS:
        raise ValueError(f"Unknown dimension {dimension!r}")
    return lambda r: getattr(r, dimension)


def summarize_by(records: Sequence[ConvertedRecord], dimension: Dimension) -> list[GroupSummary]:
    """One summary per group, largest headcount first, ties by key."""
    key = _key_fn(dimension)
    groups: dict[str, list[ConvertedRecord]] = defaultdict(list)
    for c in records:
        groups[key(c.record)].append(c)

    out: list[GroupSummary] = []
    for k, members in groups.items():
        usd = summarize([m.usd_minor for m in members])
        currencies = {m.record.currency_code for m in members}
        local_currency = next(iter(currencies)) if len(currencies) == 1 else None
        local = (
            summarize([m.record.annual_amount_minor for m in members]) if local_currency else None
        )
        assert usd is not None  # groups are never empty
        out.append(GroupSummary(k, usd, local_currency, local))
    out.sort(key=lambda g: (-g.usd.count, g.key))
    return out


@dataclass(frozen=True)
class MatrixCell:
    row: str
    col: str
    count: int
    median_usd_minor: int


def median_matrix(
    records: Sequence[ConvertedRecord], rows: Dimension, cols: Dimension
) -> list[MatrixCell]:
    """Median USD salary for every (row, col) pair that has at least one person."""
    if rows == cols:
        raise ValueError("rows and cols must be different dimensions")
    row_key, col_key = _key_fn(rows), _key_fn(cols)
    cells: dict[tuple[str, str], list[int]] = defaultdict(list)
    for c in records:
        cells[(row_key(c.record), col_key(c.record))].append(c.usd_minor)
    out = []
    for (r, c), values in sorted(cells.items()):
        s = summarize(values)
        assert s is not None
        out.append(MatrixCell(r, c, s.count, s.p50))
    return out


def usd_histogram(records: Sequence[ConvertedRecord], bins: int) -> list[Bucket]:
    return histogram([c.usd_minor for c in records], bins)
