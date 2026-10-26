"""Employee API: directory, detail, create, edit, salary changes, termination.

The clock is fixed at 2025-06-15 (see conftest).
"""

from datetime import date

import pytest

from app.models import Organization, SalaryEvent
from tests.factories import make_employee, make_org, make_rate


@pytest.fixture
def org(session, seeded):
    return session.get(Organization, seeded.org_id)


def new_employee(**overrides) -> dict:
    body = {
        "employee_number": "E90001",
        "first_name": "Grace",
        "last_name": "Hopper",
        "email": "grace@acme.example",
        "country_code": "US",
        "currency_code": "USD",
        "department": "Engineering",
        "job_title": "Staff Engineer",
        "level": "L5",
        "hire_date": "2024-01-15",
        "annual_salary": "150000.00",
    }
    body.update(overrides)
    return body


def edit_body(**overrides) -> dict:
    body = {k: v for k, v in new_employee().items() if k != "annual_salary"}
    body.update(overrides)
    return body


# ---- directory ---------------------------------------------------------------


def test_list_requires_auth(client, seeded):
    assert client.get("/employees").status_code == 401


def test_list_paginates_and_reports_total(client, session, org, viewer_headers):
    for i in range(30):
        make_employee(session, org, last_name=f"Person{i:02d}")
    session.commit()

    r = client.get("/employees?page=2&page_size=10", headers=viewer_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 30
    assert len(body["items"]) == 10
    assert body["items"][0]["last_name"] == "Person10"


def test_list_shows_salary_in_force_today_not_future_raise(client, session, org, viewer_headers):
    emp = make_employee(session, org, salary=10000000, hire_date=date(2020, 1, 1))
    session.add(
        SalaryEvent(
            organization_id=org.id,
            employee_id=emp.id,
            annual_amount_minor=12000000,
            currency_code="USD",
            effective_date=date(2025, 7, 1),  # after the fixed "today"
            reason="Annual review",
        )
    )
    session.commit()

    item = client.get("/employees", headers=viewer_headers).json()["items"][0]

    assert item["current_salary"]["annual_amount_minor"] == 10000000
    assert item["current_salary"]["annual_salary"] == "100000.00"


def test_list_filters_by_country_and_search(client, session, org, viewer_headers):
    make_employee(
        session,
        org,
        first_name="Ada",
        last_name="Lovelace",
        country_code="GB",
        currency_code="GBP",
    )
    make_employee(
        session,
        org,
        first_name="Alan",
        last_name="Turing",
        country_code="GB",
        currency_code="GBP",
    )
    make_employee(session, org, first_name="Ada", last_name="Yonath", country_code="US")
    session.commit()

    by_country = client.get("/employees?country_code=GB", headers=viewer_headers).json()
    by_name = client.get("/employees?q=ada", headers=viewer_headers).json()
    both = client.get("/employees?country_code=GB&q=ada", headers=viewer_headers).json()

    assert by_country["total"] == 2
    assert by_name["total"] == 2
    assert [e["last_name"] for e in both["items"]] == ["Lovelace"]


def test_list_excludes_terminated_by_default(client, session, org, viewer_headers):
    make_employee(session, org, last_name="Active")
    make_employee(session, org, last_name="Gone", termination_date=date(2025, 1, 31))
    session.commit()

    default = client.get("/employees", headers=viewer_headers).json()
    terminated = client.get("/employees?status=terminated", headers=viewer_headers).json()
    everyone = client.get("/employees?status=all", headers=viewer_headers).json()

    assert [e["last_name"] for e in default["items"]] == ["Active"]
    assert [e["last_name"] for e in terminated["items"]] == ["Gone"]
    assert everyone["total"] == 2


def test_list_sorts_by_current_salary_descending(client, session, org, viewer_headers):
    make_employee(session, org, last_name="Low", salary=5000000)
    make_employee(session, org, last_name="High", salary=20000000)
    make_employee(session, org, last_name="Mid", salary=9000000)
    session.commit()

    r = client.get("/employees?sort=current_salary&order=desc", headers=viewer_headers)

    assert [e["last_name"] for e in r.json()["items"]] == ["High", "Mid", "Low"]


def test_list_rejects_unknown_sort_field(client, viewer_headers):
    assert client.get("/employees?sort=password", headers=viewer_headers).status_code == 422


# ---- detail ------------------------------------------------------------------


def test_detail_includes_history_newest_first(client, session, org, admin_headers):
    emp = make_employee(session, org, hire_date=date(2022, 1, 1), salary=8000000)
    session.commit()
    client.post(
        f"/employees/{emp.id}/salary-events",
        json={"annual_salary": "90000", "effective_date": "2024-01-01", "reason": "Promotion"},
        headers=admin_headers,
    )

    body = client.get(f"/employees/{emp.id}", headers=admin_headers).json()

    assert [h["annual_salary"] for h in body["salary_history"]] == ["90000.00", "80000.00"]
    assert body["salary_history"][0]["created_by"] == "Test User"
    assert body["current_salary"]["annual_salary"] == "90000.00"


def test_detail_404_for_unknown_employee(client, admin_headers):
    assert client.get("/employees/999", headers=admin_headers).status_code == 404


def test_cannot_read_employee_of_another_organization(client, session, admin_headers):
    other = make_org(session, name="Other Co")
    emp = make_employee(session, other)
    session.commit()

    assert client.get(f"/employees/{emp.id}", headers=admin_headers).status_code == 404


# ---- create ------------------------------------------------------------------


def test_admin_creates_employee_with_starting_salary(client, admin_headers):
    r = client.post("/employees", json=new_employee(), headers=admin_headers)

    assert r.status_code == 201
    body = r.json()
    assert body["employee_number"] == "E90001"
    assert body["current_salary"]["annual_amount_minor"] == 15000000
    assert len(body["salary_history"]) == 1
    assert body["salary_history"][0]["reason"] == "Hire"
    assert body["salary_history"][0]["effective_date"] == "2024-01-15"


def test_create_respects_zero_decimal_currency(client, admin_headers):
    body = new_employee(country_code="JP", currency_code="JPY", annual_salary="9000000")
    r = client.post("/employees", json=body, headers=admin_headers)

    assert r.status_code == 201
    assert r.json()["current_salary"]["annual_amount_minor"] == 9000000


def test_create_rejects_fractional_yen(client, admin_headers):
    body = new_employee(country_code="JP", currency_code="JPY", annual_salary="9000000.5")
    r = client.post("/employees", json=body, headers=admin_headers)

    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "annual_salary"


def test_create_reports_all_field_errors_at_once(client, admin_headers):
    body = new_employee(country_code="XX", department="Nope", email="bad")
    r = client.post("/employees", json=body, headers=admin_headers)

    assert r.status_code == 422
    fields = {e["field"] for e in r.json()["errors"]}
    assert {"country_code", "department", "email"} <= fields


def test_create_rejects_duplicate_employee_number(client, admin_headers):
    client.post("/employees", json=new_employee(), headers=admin_headers)
    r = client.post(
        "/employees", json=new_employee(email="other@acme.example"), headers=admin_headers
    )

    assert r.status_code == 422
    assert r.json()["errors"] == [{"field": "employee_number", "message": "is already in use"}]


def test_viewer_cannot_create(client, viewer_headers):
    r = client.post("/employees", json=new_employee(), headers=viewer_headers)
    assert r.status_code == 403


# ---- edit / salary change ----------------------------------------------------


def test_update_with_stale_version_is_conflict(client, admin_headers):
    created = client.post("/employees", json=new_employee(), headers=admin_headers).json()
    url = f"/employees/{created['id']}"
    body = edit_body(job_title="Principal Engineer", version=1)

    first = client.put(url, json=body, headers=admin_headers)
    second = client.put(url, json=body, headers=admin_headers)

    assert first.status_code == 200
    assert first.json()["job_title"] == "Principal Engineer"
    assert first.json()["version"] == 2
    assert second.status_code == 409


def test_update_can_record_salary_change_in_same_request(client, admin_headers):
    created = client.post("/employees", json=new_employee(), headers=admin_headers).json()
    body = edit_body(
        level="L6",
        version=1,
        salary_change={
            "annual_salary": "175000",
            "effective_date": "2025-04-01",
            "reason": "Promotion",
        },
    )

    r = client.put(f"/employees/{created['id']}", json=body, headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["level"] == "L6"
    assert r.json()["current_salary"]["annual_salary"] == "175000.00"


def test_currency_change_requires_salary_in_new_currency(client, admin_headers):
    created = client.post("/employees", json=new_employee(), headers=admin_headers).json()
    body = edit_body(country_code="GB", currency_code="GBP", version=1)

    r = client.put(f"/employees/{created['id']}", json=body, headers=admin_headers)

    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "currency_code"


def test_salary_event_on_existing_date_is_rejected(client, admin_headers):
    created = client.post("/employees", json=new_employee(), headers=admin_headers).json()
    r = client.post(
        f"/employees/{created['id']}/salary-events",
        json={"annual_salary": "160000", "effective_date": "2024-01-15", "reason": "Correction"},
        headers=admin_headers,
    )

    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "effective_date"


def test_viewer_cannot_change_salary(client, session, org, viewer_headers):
    emp = make_employee(session, org)
    session.commit()
    r = client.post(
        f"/employees/{emp.id}/salary-events",
        json={"annual_salary": "1", "effective_date": "2025-01-01", "reason": "x"},
        headers=viewer_headers,
    )
    assert r.status_code == 403


# ---- terminate / reactivate --------------------------------------------------


def test_terminate_then_reactivate(client, admin_headers):
    created = client.post("/employees", json=new_employee(), headers=admin_headers).json()
    eid = created["id"]

    t = client.post(
        f"/employees/{eid}/terminate",
        json={"termination_date": "2025-05-31", "version": 1},
        headers=admin_headers,
    )
    assert t.status_code == 200
    assert t.json()["is_active"] is False

    again = client.post(f"/employees/{eid}/reactivate", json={"version": 2}, headers=admin_headers)
    assert again.status_code == 200
    assert again.json()["is_active"] is True
    assert again.json()["termination_date"] is None


def test_future_termination_keeps_employee_active_today(client, admin_headers):
    created = client.post("/employees", json=new_employee(), headers=admin_headers).json()
    r = client.post(
        f"/employees/{created['id']}/terminate",
        json={"termination_date": "2025-12-31", "version": 1},
        headers=admin_headers,
    )

    assert r.json()["is_active"] is True


def test_reactivating_active_employee_is_conflict(client, admin_headers):
    created = client.post("/employees", json=new_employee(), headers=admin_headers).json()
    r = client.post(
        f"/employees/{created['id']}/reactivate", json={"version": 1}, headers=admin_headers
    )
    assert r.status_code == 409


def test_reference_lists_countries_with_currency(client, viewer_headers):
    body = client.get("/reference", headers=viewer_headers).json()
    jp = next(c for c in body["countries"] if c["code"] == "JP")
    assert jp["currency_code"] == "JPY"
    assert "Engineering" in body["departments"]


def test_salary_sort_compares_currencies_in_usd(client, session, org, viewer_headers):
    make_rate(session, "INR", "0.0114")
    make_rate(session, "JPY", "0.0067")
    # Raw amounts: INR 11.5M and JPY 9M dwarf USD 300k, but in USD they are
    # about 131k and 60k, so the American is the highest paid.
    make_employee(session, org, last_name="India", country_code="IN", currency_code="INR",
                  salary=1_150_000_000)  # fmt: skip
    make_employee(session, org, last_name="Japan", country_code="JP", currency_code="JPY",
                  salary=9_000_000)  # fmt: skip
    make_employee(session, org, last_name="States", salary=30_000_000)
    session.commit()

    r = client.get("/employees?sort=current_salary&order=desc", headers=viewer_headers)

    assert [e["last_name"] for e in r.json()["items"]] == ["States", "India", "Japan"]


def test_employee_without_salary_sorts_last_both_ways(client, session, org, viewer_headers):
    make_employee(session, org, last_name="Paid", salary=5_000_000)
    make_employee(session, org, last_name="Unpaid", salary=None)
    session.commit()

    for order in ("asc", "desc"):
        r = client.get(f"/employees?sort=current_salary&order={order}", headers=viewer_headers)
        assert [e["last_name"] for e in r.json()["items"]] == ["Paid", "Unpaid"]
