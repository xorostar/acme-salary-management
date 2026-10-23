from datetime import date

import pytest

from app.domain.errors import ValidationError
from app.domain.salary import SalaryPoint, current_salary, validate_salary_event

HIRE = date(2020, 1, 15)


def point(y, m, d, amount=5000000, ccy="USD"):
    return SalaryPoint(date(y, m, d), amount, ccy)


class TestCurrentSalary:
    def test_none_when_no_events(self):
        assert current_salary([], date(2025, 1, 1)) is None

    def test_none_when_all_events_are_in_the_future(self):
        assert current_salary([point(2026, 1, 1)], date(2025, 6, 15)) is None

    def test_picks_latest_on_or_before_reference_date(self):
        events = [point(2020, 1, 15, 100), point(2022, 4, 1, 200), point(2024, 4, 1, 300)]
        assert current_salary(events, date(2023, 12, 31)).annual_amount_minor == 200

    def test_event_on_reference_date_counts(self):
        events = [point(2020, 1, 15, 100), point(2025, 6, 15, 200)]
        assert current_salary(events, date(2025, 6, 15)).annual_amount_minor == 200

    def test_ignores_future_dated_raise(self):
        events = [point(2020, 1, 15, 100), point(2025, 7, 1, 200)]
        assert current_salary(events, date(2025, 6, 15)).annual_amount_minor == 100

    def test_order_of_input_does_not_matter(self):
        events = [point(2024, 1, 1, 300), point(2020, 1, 15, 100), point(2022, 1, 1, 200)]
        assert current_salary(events, date(2025, 1, 1)).annual_amount_minor == 300


def valid_kwargs(**overrides):
    base = dict(
        hire_date=HIRE,
        employee_currency="USD",
        existing_effective_dates=[HIRE],
        annual_amount_minor=6000000,
        currency_code="USD",
        effective_date=date(2024, 4, 1),
        reason="Annual review",
    )
    base.update(overrides)
    return base


def errors_by_field(exc: ValidationError) -> dict[str, str]:
    return {e.field: e.message for e in exc.errors}


class TestValidateSalaryEvent:
    def test_valid_event_passes(self):
        validate_salary_event(**valid_kwargs())

    @pytest.mark.parametrize("amount", [0, -1, -5000000])
    def test_rejects_non_positive_amount(self, amount):
        with pytest.raises(ValidationError) as exc:
            validate_salary_event(**valid_kwargs(annual_amount_minor=amount))
        assert "greater than zero" in errors_by_field(exc.value)["annual_amount_minor"]

    def test_rejects_absurd_amount(self):
        with pytest.raises(ValidationError) as exc:
            validate_salary_event(**valid_kwargs(annual_amount_minor=10**14))
        assert "annual_amount_minor" in errors_by_field(exc.value)

    def test_rejects_bool_as_amount(self):
        with pytest.raises(ValidationError):
            validate_salary_event(**valid_kwargs(annual_amount_minor=True))

    def test_rejects_currency_mismatch(self):
        with pytest.raises(ValidationError) as exc:
            validate_salary_event(**valid_kwargs(currency_code="GBP"))
        msg = errors_by_field(exc.value)["currency_code"]
        assert "must match the employee's currency USD" in msg

    def test_rejects_unsupported_currency(self):
        with pytest.raises(ValidationError) as exc:
            validate_salary_event(**valid_kwargs(currency_code="XXX"))
        assert "unsupported" in errors_by_field(exc.value)["currency_code"]

    def test_rejects_effective_date_before_hire(self):
        with pytest.raises(ValidationError) as exc:
            validate_salary_event(**valid_kwargs(effective_date=date(2019, 12, 31)))
        assert "before hire date 2020-01-15" in errors_by_field(exc.value)["effective_date"]

    def test_allows_effective_date_equal_to_hire_when_no_event_exists(self):
        validate_salary_event(**valid_kwargs(existing_effective_dates=[], effective_date=HIRE))

    def test_rejects_duplicate_effective_date(self):
        with pytest.raises(ValidationError) as exc:
            validate_salary_event(**valid_kwargs(effective_date=HIRE))
        assert "already exists" in errors_by_field(exc.value)["effective_date"]

    def test_allows_future_dated_event(self):
        validate_salary_event(**valid_kwargs(effective_date=date(2030, 1, 1)))

    @pytest.mark.parametrize("reason", ["", "   ", None])
    def test_rejects_missing_reason(self, reason):
        with pytest.raises(ValidationError) as exc:
            validate_salary_event(**valid_kwargs(reason=reason))
        assert errors_by_field(exc.value)["reason"] == "is required"

    def test_rejects_overlong_reason(self):
        with pytest.raises(ValidationError):
            validate_salary_event(**valid_kwargs(reason="x" * 201))

    def test_collects_all_errors_at_once(self):
        with pytest.raises(ValidationError) as exc:
            validate_salary_event(
                **valid_kwargs(
                    annual_amount_minor=0,
                    currency_code="GBP",
                    effective_date=date(2019, 1, 1),
                    reason="",
                )
            )
        assert set(errors_by_field(exc.value)) == {
            "annual_amount_minor",
            "currency_code",
            "effective_date",
            "reason",
        }
