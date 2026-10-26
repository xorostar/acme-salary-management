"""The seed generator is deterministic and every record it produces would pass
the same validation the API applies to user input."""

from collections import Counter

import pytest
from sqlalchemy import func, select

from app.domain.employee import EmployeeInput, validate_employee
from app.domain.reference import COUNTRIES
from app.domain.salary import validate_salary_event
from app.models import Employee, ExchangeRate, SalaryEvent, User
from app.seed import DatabaseNotEmptyError, seed_database
from app.seed.generator import ANCHOR_DATE, generate_employees, job_title

SAMPLE = 500  # big enough to cover every country and level, small enough to be fast


@pytest.fixture(scope="module")
def people():
    return generate_employees(SAMPLE)


def test_same_seed_gives_identical_output(people):
    assert generate_employees(SAMPLE) == people


def test_different_seed_gives_different_output(people):
    assert generate_employees(SAMPLE, seed=1) != people


def test_employee_numbers_and_emails_are_unique(people):
    assert len({p.employee_number for p in people}) == SAMPLE
    assert len({p.email for p in people}) == SAMPLE


def test_every_employee_passes_domain_validation(people):
    for p in people:
        validate_employee(
            EmployeeInput(
                employee_number=p.employee_number,
                first_name=p.first_name,
                last_name=p.last_name,
                email=p.email,
                country_code=p.country_code,
                currency_code=p.currency_code,
                department=p.department,
                job_title=p.job_title,
                level=p.level,
                hire_date=p.hire_date,
                termination_date=p.termination_date,
            )
        )


def test_every_salary_history_passes_domain_rules(people):
    for p in people:
        assert p.salary_events, p.employee_number
        assert p.salary_events[0].effective_date == p.hire_date
        assert p.salary_events[0].reason == "Hire"
        seen = []
        for e in p.salary_events:
            validate_salary_event(
                hire_date=p.hire_date,
                employee_currency=p.currency_code,
                existing_effective_dates=seen,
                annual_amount_minor=e.annual_amount_minor,
                currency_code=p.currency_code,
                effective_date=e.effective_date,
                reason=e.reason,
            )
            seen.append(e.effective_date)


def test_salaries_never_decrease_over_history(people):
    for p in people:
        amounts = [e.annual_amount_minor for e in p.salary_events]
        assert amounts == sorted(amounts), p.employee_number


def test_currency_always_matches_country(people):
    for p in people:
        assert p.currency_code == COUNTRIES[p.country_code].currency_code


def test_nothing_is_dated_after_the_anchor(people):
    for p in people:
        assert p.hire_date <= ANCHOR_DATE
        assert all(e.effective_date <= ANCHOR_DATE for e in p.salary_events)
        if p.termination_date:
            assert p.hire_date <= p.termination_date <= ANCHOR_DATE


def test_distribution_covers_every_country_and_is_weighted(people):
    by_country = Counter(p.country_code for p in people)
    assert set(by_country) == set(COUNTRIES)
    assert by_country.most_common(1)[0][0] == "US"


def test_yen_salaries_are_whole_numbers_of_ten_thousand(people):
    for p in people:
        if p.currency_code == "JPY":
            assert all(e.annual_amount_minor % 10_000 == 0 for e in p.salary_events)


def test_job_titles_follow_level():
    assert job_title("Engineering", "L4") == "Senior Software Engineer"
    assert job_title("Engineering", "L2") == "Software Engineer I"
    assert job_title("Sales", "M1") == "Sales Manager"
    assert job_title("Legal", "VP") == "VP, Legal"


def test_seed_database_loads_everything(session):
    result = seed_database(session, demo_password="pw", count=50)

    assert result.employees == 50
    assert session.scalar(select(func.count(Employee.id))) == 50
    assert session.scalar(select(func.count(SalaryEvent.id))) == result.salary_events
    assert session.scalar(select(func.count(ExchangeRate.id))) == result.exchange_rates
    assert {u.role for u in session.scalars(select(User))} == {"hr_admin", "hr_viewer"}


def test_seed_refuses_to_overwrite_without_reset(session):
    seed_database(session, demo_password="pw", count=5)

    with pytest.raises(DatabaseNotEmptyError):
        seed_database(session, demo_password="pw", count=5)

    seed_database(session, demo_password="pw", count=7, reset=True)
    assert session.scalar(select(func.count(Employee.id))) == 7
