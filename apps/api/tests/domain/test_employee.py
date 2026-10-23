from datetime import date

import pytest

from app.domain.employee import EmployeeInput, is_active, normalize_employee, validate_employee
from app.domain.errors import ValidationError


def make(**overrides) -> EmployeeInput:
    base = dict(
        employee_number="E00001",
        first_name="Ada",
        last_name="Lovelace",
        email="ada@acme.example",
        country_code="GB",
        currency_code="GBP",
        department="Engineering",
        job_title="Software Engineer",
        level="L3",
        hire_date=date(2021, 3, 1),
        termination_date=None,
    )
    base.update(overrides)
    return EmployeeInput(**base)


def fields(exc: ValidationError) -> set[str]:
    return {e.field for e in exc.errors}


class TestNormalize:
    def test_trims_and_normalizes_case(self):
        n = normalize_employee(
            make(
                employee_number=" e00001 ",
                email=" Ada@ACME.example ",
                country_code="gb",
                currency_code="gbp",
                level="l3",
                first_name="  Ada ",
            )
        )
        assert n.employee_number == "E00001"
        assert n.email == "ada@acme.example"
        assert n.country_code == "GB"
        assert n.currency_code == "GBP"
        assert n.level == "L3"
        assert n.first_name == "Ada"

    def test_is_idempotent(self):
        once = normalize_employee(make(email=" X@Y.Z "))
        assert normalize_employee(once) == once


class TestValidate:
    def test_valid_input_returns_normalized(self):
        out = validate_employee(make(email="ADA@acme.example"))
        assert out.email == "ada@acme.example"

    @pytest.mark.parametrize("number", ["", "-E1", "E 1", "E" * 21, "e#1"])
    def test_bad_employee_number(self, number):
        with pytest.raises(ValidationError) as exc:
            validate_employee(make(employee_number=number))
        assert "employee_number" in fields(exc.value)

    @pytest.mark.parametrize("email", ["", "ada", "ada@", "@acme.example", "a b@acme.example"])
    def test_bad_email(self, email):
        with pytest.raises(ValidationError) as exc:
            validate_employee(make(email=email))
        assert "email" in fields(exc.value)

    def test_blank_names(self):
        with pytest.raises(ValidationError) as exc:
            validate_employee(make(first_name="  ", last_name=""))
        assert {"first_name", "last_name"} <= fields(exc.value)

    def test_unknown_country_currency_department_level(self):
        with pytest.raises(ValidationError) as exc:
            validate_employee(
                make(country_code="ZZ", currency_code="ZZZ", department="Magic", level="L99")
            )
        assert {"country_code", "currency_code", "department", "level"} <= fields(exc.value)

    def test_currency_need_not_match_country(self):
        # An employee in Germany paid in USD is a valid arrangement.
        validate_employee(make(country_code="DE", currency_code="USD"))

    def test_termination_before_hire(self):
        with pytest.raises(ValidationError) as exc:
            validate_employee(make(termination_date=date(2021, 2, 28)))
        assert "termination_date" in fields(exc.value)

    def test_termination_on_hire_date_is_allowed(self):
        validate_employee(make(termination_date=date(2021, 3, 1)))

    def test_blank_job_title(self):
        with pytest.raises(ValidationError) as exc:
            validate_employee(make(job_title=" "))
        assert "job_title" in fields(exc.value)


class TestIsActive:
    def test_no_termination_is_active(self):
        assert is_active(None, date(2025, 6, 15))

    def test_future_termination_is_still_active(self):
        assert is_active(date(2025, 6, 16), date(2025, 6, 15))

    def test_termination_today_is_inactive(self):
        assert not is_active(date(2025, 6, 15), date(2025, 6, 15))

    def test_past_termination_is_inactive(self):
        assert not is_active(date(2024, 1, 1), date(2025, 6, 15))
