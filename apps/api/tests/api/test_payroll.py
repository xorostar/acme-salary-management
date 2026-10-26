"""Payroll runs. Fixed today is 2025-06-15; GBP rate 1.25 from 2025-01-01."""

import csv
import io
from datetime import date

import pytest

from app.models import Organization, SalaryEvent
from tests.factories import make_employee, make_rate


@pytest.fixture
def org(session, seeded):
    org = session.get(Organization, seeded.org_id)
    make_rate(session, "GBP", "1.25")
    session.commit()
    return org


def run(client, headers, year=2025, month=5):
    return client.post("/payroll-runs", json={"year": year, "month": month}, headers=headers)


def test_run_snapshots_employees_employed_at_period_end(client, session, org, admin_headers):
    make_employee(session, org, employee_number="A", salary=12_000_000)  # USD 10,000/mo
    make_employee(session, org, employee_number="B", country_code="GB", currency_code="GBP",
                  salary=6_000_000)  # GBP 5,000/mo = USD 6,250  # fmt: skip
    make_employee(session, org, employee_number="C", termination_date=date(2025, 5, 20))
    make_employee(session, org, employee_number="D", hire_date=date(2025, 6, 1))
    session.commit()

    r = run(client, admin_headers)

    assert r.status_code == 201
    body = r.json()
    assert body["employee_count"] == 2
    assert body["total_usd_minor"] == 1_000_000 + 625_000
    countries = {c["country_code"]: c for c in body["countries"]}
    assert countries["GB"]["amount_minor"] == 500_000
    assert countries["GB"]["amount_usd_minor"] == 625_000
    assert countries["GB"]["country_name"] == "United Kingdom"


def test_run_uses_salary_in_force_at_period_end(client, session, org, admin_headers):
    emp = make_employee(session, org, salary=12_000_000, hire_date=date(2020, 1, 1))
    session.add(SalaryEvent(organization_id=org.id, employee_id=emp.id,
                            annual_amount_minor=24_000_000, currency_code="USD",
                            effective_date=date(2025, 6, 1), reason="Promotion"))  # fmt: skip
    session.commit()

    may = run(client, admin_headers, month=5).json()
    june = run(client, admin_headers, month=6).json()

    assert may["total_usd_minor"] == 1_000_000
    assert june["total_usd_minor"] == 2_000_000


def test_run_is_frozen_after_salary_changes(client, session, org, admin_headers):
    emp = make_employee(session, org, salary=12_000_000, hire_date=date(2020, 1, 1))
    session.commit()
    created = run(client, admin_headers).json()

    client.post(f"/employees/{emp.id}/salary-events",
                json={"annual_salary": "999999", "effective_date": "2025-05-01",
                      "reason": "Correction"},
                headers=admin_headers)  # fmt: skip

    again = client.get(f"/payroll-runs/{created['id']}", headers=admin_headers).json()
    assert again["total_usd_minor"] == 1_000_000


def test_second_run_for_same_period_is_conflict(client, org, admin_headers):
    assert run(client, admin_headers).status_code == 201
    assert run(client, admin_headers).status_code == 409


def test_run_too_far_ahead_is_rejected(client, org, admin_headers):
    r = run(client, admin_headers, month=8)
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "month"


def test_missing_rate_refuses_run(client, session, org, admin_headers):
    make_employee(session, org, country_code="BR", currency_code="BRL")
    session.commit()

    r = run(client, admin_headers)

    assert r.status_code == 422
    assert "BRL" in r.json()["errors"][0]["message"]
    assert client.get("/payroll-runs", headers=admin_headers).json() == []


def test_viewer_can_read_but_not_create(client, org, admin_headers, viewer_headers):
    assert run(client, viewer_headers).status_code == 403
    created = run(client, admin_headers).json()
    assert client.get(f"/payroll-runs/{created['id']}", headers=viewer_headers).status_code == 200


def test_list_runs_newest_period_first(client, org, admin_headers):
    run(client, admin_headers, month=3)
    run(client, admin_headers, month=5)
    runs = client.get("/payroll-runs", headers=admin_headers).json()
    assert [(r["period_year"], r["period_month"]) for r in runs] == [(2025, 5), (2025, 3)]


def test_lines_are_paginated_and_filterable(client, session, org, admin_headers):
    for i in range(5):
        make_employee(session, org, employee_number=f"U{i}")
    make_employee(session, org, employee_number="G1", country_code="GB", currency_code="GBP")
    session.commit()
    rid = run(client, admin_headers).json()["id"]

    page = client.get(f"/payroll-runs/{rid}/lines?page_size=2&page=2", headers=admin_headers)
    gb = client.get(f"/payroll-runs/{rid}/lines?country_code=GB", headers=admin_headers)

    assert page.json()["total"] == 6
    assert [ln["employee_number"] for ln in page.json()["items"]] == ["U1", "U2"]  # G1 sorts first
    assert [ln["employee_number"] for ln in gb.json()["items"]] == ["G1"]
    assert gb.json()["items"][0]["rate_to_usd"] == "1.25"


def test_export_run_csv(client, session, org, admin_headers):
    make_employee(session, org, employee_number="A", salary=12_000_000)
    session.commit()
    rid = run(client, admin_headers).json()["id"]

    r = client.get(f"/payroll-runs/{rid}/export.csv", headers=admin_headers)

    assert "acme-payroll-2025-05.csv" in r.headers["content-disposition"]
    (row,) = csv.DictReader(io.StringIO(r.text))
    assert row["monthly_amount"] == "10000.00"
    assert row["monthly_amount_usd"] == "10000.00"


def test_unknown_run_is_404(client, org, admin_headers):
    assert client.get("/payroll-runs/999", headers=admin_headers).status_code == 404
