"""Descriptive statistics over integer amounts.

Percentiles use linear interpolation between order statistics (the same
definition as numpy's default and Excel's PERCENTILE.INC), rounded half-up to
a whole minor unit. Computed in Python because the inputs are already in
memory after currency conversion and 10,000 values take well under a
millisecond.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


def _round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def percentile(sorted_values: Sequence[int], p: int) -> int:
    """p-th percentile (0..100) of an ascending-sorted non-empty sequence."""
    if not sorted_values:
        raise ValueError("percentile of empty sequence")
    if not 0 <= p <= 100:
        raise ValueError("p must be between 0 and 100")
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    rank = Decimal(p) * (n - 1) / Decimal(100)
    lower = int(rank)  # floor, rank is non-negative
    upper = min(lower + 1, n - 1)
    fraction = rank - lower
    lo, hi = Decimal(sorted_values[lower]), Decimal(sorted_values[upper])
    return _round_half_up(lo + (hi - lo) * fraction)


def mean(values: Sequence[int]) -> int:
    if not values:
        raise ValueError("mean of empty sequence")
    return _round_half_up(Decimal(sum(values)) / Decimal(len(values)))


@dataclass(frozen=True)
class Summary:
    count: int
    total: int
    mean: int
    min: int
    max: int
    p10: int
    p25: int
    p50: int
    p75: int
    p90: int


def summarize(values: Sequence[int]) -> Summary | None:
    """Full summary, or None for an empty group (the API renders that as "no data")."""
    if not values:
        return None
    s = sorted(values)
    return Summary(
        count=len(s),
        total=sum(s),
        mean=mean(s),
        min=s[0],
        max=s[-1],
        p10=percentile(s, 10),
        p25=percentile(s, 25),
        p50=percentile(s, 50),
        p75=percentile(s, 75),
        p90=percentile(s, 90),
    )


@dataclass(frozen=True)
class Bucket:
    start: int  # inclusive
    end: int  # exclusive, except the last bucket which includes max
    count: int


def histogram(values: Sequence[int], bins: int) -> list[Bucket]:
    """Equal-width buckets from min to max. A single distinct value gives one bucket."""
    if bins <= 0:
        raise ValueError("bins must be positive")
    if not values:
        return []
    lo, hi = min(values), max(values)
    if lo == hi:
        return [Bucket(lo, hi, len(values))]
    width = -(-(hi - lo) // bins)  # ceiling division so the last bucket reaches max
    counts = [0] * bins
    for v in values:
        idx = min((v - lo) // width, bins - 1)
        counts[idx] += 1
    return [Bucket(lo + i * width, lo + (i + 1) * width, counts[i]) for i in range(bins)]
