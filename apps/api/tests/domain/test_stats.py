import pytest

from app.domain.stats import Bucket, histogram, mean, percentile, summarize


class TestPercentile:
    def test_single_value(self):
        assert percentile([42], 50) == 42
        assert percentile([42], 0) == 42
        assert percentile([42], 100) == 42

    def test_median_of_odd_count(self):
        assert percentile([1, 2, 3, 4, 5], 50) == 3

    def test_median_of_even_count_interpolates(self):
        assert percentile([1, 2, 3, 4], 50) == 3  # 2.5 rounds half-up to 3
        assert percentile([10, 20, 30, 40], 50) == 25

    def test_matches_excel_percentile_inc(self):
        # PERCENTILE.INC({15,20,35,40,50}, 0.4) = 29
        assert percentile([15, 20, 35, 40, 50], 40) == 29

    def test_extremes(self):
        values = [5, 1, 3]
        s = sorted(values)
        assert percentile(s, 0) == 1
        assert percentile(s, 100) == 5

    def test_rounds_half_up(self):
        # p25 of [1,2]: rank 0.25 -> 1.25 -> 1 ; p75 -> 1.75 -> 2 ; p50 -> 1.5 -> 2
        assert percentile([1, 2], 25) == 1
        assert percentile([1, 2], 50) == 2
        assert percentile([1, 2], 75) == 2

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            percentile([], 50)

    @pytest.mark.parametrize("p", [-1, 101])
    def test_rejects_out_of_range_p(self, p):
        with pytest.raises(ValueError):
            percentile([1], p)


class TestMean:
    def test_rounds_half_up(self):
        assert mean([1, 2]) == 2
        assert mean([1, 2, 2]) == 2  # 1.666 -> 2
        assert mean([1, 1, 2]) == 1  # 1.333 -> 1

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            mean([])


class TestSummarize:
    def test_empty_returns_none(self):
        assert summarize([]) is None

    def test_known_values(self):
        s = summarize([50, 10, 40, 20, 30])
        assert s.count == 5
        assert s.total == 150
        assert s.mean == 30
        assert s.min == 10
        assert s.max == 50
        assert s.p50 == 30
        assert s.p10 == 14
        assert s.p90 == 46

    def test_unsorted_input_is_sorted_internally(self):
        assert summarize([3, 1, 2]).p50 == 2


class TestHistogram:
    def test_empty(self):
        assert histogram([], 5) == []

    def test_single_distinct_value_one_bucket(self):
        assert histogram([7, 7, 7], 5) == [Bucket(7, 7, 3)]

    def test_counts_sum_to_input_size(self):
        values = list(range(0, 100))
        buckets = histogram(values, 7)
        assert sum(b.count for b in buckets) == 100
        assert len(buckets) == 7

    def test_max_value_lands_in_last_bucket(self):
        buckets = histogram([0, 10], 2)
        assert buckets[0] == Bucket(0, 5, 1)
        assert buckets[1] == Bucket(5, 10, 1)

    def test_buckets_are_contiguous(self):
        buckets = histogram([3, 9, 27, 81], 4)
        for a, b in zip(buckets, buckets[1:], strict=False):
            assert a.end == b.start

    def test_rejects_non_positive_bins(self):
        with pytest.raises(ValueError):
            histogram([1], 0)
