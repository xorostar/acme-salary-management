"""Analytics endpoints over a tiny hand-built organization.

Fixed today is 2025-06-15. Rates: GBP 1.25, JPY 0.0067 (2025-01-01).
"""

from datetime import date

import pytest

from app.models import Organization, SalaryEvent
from tests.factories import make_employee, make_rate


@pytest.fixture
def org(session, seeded):
    org = session.get(Organization, seeded.org_id)
    make_rate(session, "GBP", "1.25")
    make_rate(session, "JPY", "0.0067")
    make_rate(session, "GBP", "2.00", effective=date(2026, 1, 1))  # not yet in force
    # US: 100k, 120k, 200k  |  GB: 80k GBP = 100k USD  |  JP: 10M JPY = 67k USD
    make_employee(session, org, salary=10_000_000, level="L3")
    make_employee(session, org, salary=12_000_000, level="L3", department="Sales")
    make_employee(session, org, salary=20_000_000, level="L5")
    make_employee(session, org, country_code="GB", currency_code="GBP", salary=8_000_000)
    make_employee(session, org, country_code="JP", currency_code="JPY", salary=10_000_000)
    # Excluded: terminated, and hired after today.
    make_employee(session, org, salary=99_000_000, termination_date=date(2025, 1, 1))
    make_employee(session, org, salary=99_000_000, hire_date=date(2025, 9, 1))
    session.commit()
    return org


def test_overview_counts_active_employees_in_usd(client, org, viewer_headers):
    body = client.get("/analytics/overview", headers=viewer_headers).json()

    assert body["as_of"] == "2025-06-15"
    assert body["headcount"] == 5
    usd = body["annual_payroll_usd"]
    assert usd["total"] == 10_000_000 + 12_000_000 + 20_000_000 + 10_000_000 + 6_700_000
    assert usd["p50"] == 10_000_000
    assert usd["min"] == 6_700_000
    assert usd["max"] == 20_000_000
    assert body["missing_rates"] == []


def test_overview_reports_rates_in_force_not_future_ones(client, org, viewer_headers):
    rates = client.get("/analytics/overview", headers=viewer_headers).json()["rates"]
    gbp = next(r for r in rates if r["currency_code"] == "GBP")
    assert gbp == {"currency_code": "GBP", "rate_to_usd": "1.25", "effective_date": "2025-01-01"}


def test_salary_raise_dated_in_future_does_not_count(client, session, org, viewer_headers):
    emp = make_employee(session, org, salary=5_000_000)
    session.add(SalaryEvent(organization_id=org.id, employee_id=emp.id,
                            annual_amount_minor=90_000_000, currency_code="USD",
                            effective_date=date(2025, 12, 1), reason="Promotion"))  # fmt: skip
    session.commit()

    usd = client.get("/analytics/overview", headers=viewer_headers).json()["annual_payroll_usd"]
    assert usd["max"] == 20_000_000


def test_overview_filters(client, org, viewer_headers):
    body = client.get("/analytics/overview?country_code=US&level=L3", headers=viewer_headers)
    assert body.json()["headcount"] == 2
    assert body.json()["annual_payroll_usd"]["mean"] == 11_000_000


def test_overview_of_empty_filter_has_no_summary(client, org, viewer_headers):
    body = client.get("/analytics/overview?country_code=BR", headers=viewer_headers).json()
    assert body["headcount"] == 0
    assert body["annual_payroll_usd"] is None
    assert body["histogram"] == []


def test_breakdown_by_country_has_local_and_usd_medians(client, org, viewer_headers):
    body = client.get("/analytics/breakdown?by=country_code", headers=viewer_headers).json()

    groups = {g["key"]: g for g in body["groups"]}
    assert body["groups"][0]["key"] == "US"  # largest first
    assert groups["US"]["usd"]["p50"] == 12_000_000
    assert groups["GB"]["label"] == "United Kingdom"
    assert groups["GB"]["local_currency"] == "GBP"
    assert groups["GB"]["local"]["p50"] == 8_000_000
    assert groups["GB"]["usd"]["p50"] == 10_000_000
    assert groups["JP"]["local"]["p50"] == 10_000_000
    assert groups["JP"]["usd"]["p50"] == 6_700_000


def test_breakdown_by_department_mixes_currencies(client, org, viewer_headers):
    body = client.get("/analytics/breakdown?by=department", headers=viewer_headers).json()
    eng = next(g for g in body["groups"] if g["key"] == "Engineering")
    assert eng["usd"]["count"] == 4
    assert eng["local"] is None


def test_matrix_level_by_country(client, org, viewer_headers):
    body = client.get("/analytics/matrix?rows=level&cols=country_code", headers=viewer_headers)
    cells = {(c["row"], c["col"]): c for c in body.json()["cells"]}
    assert cells[("L3", "US")]["median_usd"] == 11_000_000
    assert cells[("L5", "US")]["count"] == 1


def test_matrix_rejects_same_dimension_twice(client, org, viewer_headers):
    r = client.get("/analytics/matrix?rows=level&cols=level", headers=viewer_headers)
    assert r.status_code == 422


def test_currency_without_rate_is_reported_not_guessed(client, session, org, viewer_headers):
    make_employee(session, org, country_code="BR", currency_code="BRL", salary=1)
    session.commit()

    body = client.get("/analytics/overview", headers=viewer_headers).json()
    assert body["missing_rates"] == ["BRL"]
    assert body["headcount"] == 5


def test_analytics_requires_login(client, org):
    assert client.get("/analytics/overview").status_code == 401
