import csv
import io
from datetime import date

import pytest

from app.domain.csv_io import IMPORT_COLUMNS
from app.models import Organization
from tests.factories import make_employee

HEADER = ",".join(IMPORT_COLUMNS)
ROW1 = "N1,Ada,Lovelace,ada@acme.example,GB,GBP,Engineering,Engineer,L3,2024-01-15,65000.50"
ROW2 = "N2,Alan,Turing,alan@acme.example,JP,JPY,Engineering,Engineer,L4,2023-05-01,9000000"


def upload(client, headers, text: str, dry_run: bool = False):
    return client.post(
        f"/employees/import?dry_run={'true' if dry_run else 'false'}",
        files={"file": ("hires.csv", text.encode(), "text/csv")},
        headers=headers,
    )


@pytest.fixture
def org(session, seeded):
    return session.get(Organization, seeded.org_id)


def test_import_creates_employees_with_hire_salary(client, admin_headers):
    r = upload(client, admin_headers, f"{HEADER}\n{ROW1}\n{ROW2}\n")

    assert r.status_code == 200
    assert r.json() == {
        "total_rows": 2,
        "imported": 2,
        "dry_run": False,
        "error_count": 0,
        "errors": [],
    }
    listing = client.get("/employees?sort=employee_number", headers=admin_headers).json()
    assert [e["employee_number"] for e in listing["items"]] == ["N1", "N2"]
    detail = client.get(f"/employees/{listing['items'][0]['id']}", headers=admin_headers).json()
    assert detail["salary_history"][0]["reason"] == "Hire"
    assert detail["salary_history"][0]["created_by"] == "Test User"
    assert detail["current_salary"]["annual_salary"] == "65000.50"


def test_dry_run_validates_without_saving(client, admin_headers):
    r = upload(client, admin_headers, f"{HEADER}\n{ROW1}\n", dry_run=True)

    assert r.json()["imported"] == 1
    assert r.json()["dry_run"] is True
    assert client.get("/employees", headers=admin_headers).json()["total"] == 0


def test_one_bad_row_rejects_the_whole_file(client, admin_headers):
    bad = ROW2.replace(",JP,", ",ZZ,")
    r = upload(client, admin_headers, f"{HEADER}\n{ROW1}\n{bad}\n")

    assert r.status_code == 422
    assert r.json()["errors"] == [
        {"row": 3, "field": "country_code", "message": "unsupported country 'ZZ'"}
    ]
    assert client.get("/employees", headers=admin_headers).json()["total"] == 0


def test_import_detects_existing_employee_numbers(client, session, org, admin_headers):
    make_employee(session, org, employee_number="N1")
    session.commit()

    r = upload(client, admin_headers, f"{HEADER}\n{ROW1}\n")

    assert r.status_code == 422
    assert r.json()["errors"][0] == {"row": 2, "field": "employee_number",
                                     "message": "already exists"}  # fmt: skip


def test_viewer_cannot_import(client, viewer_headers):
    assert upload(client, viewer_headers, f"{HEADER}\n{ROW1}\n").status_code == 403


def test_non_utf8_file_is_rejected(client, admin_headers):
    r = client.post("/employees/import", files={"file": ("x.csv", b"\xff\xfe\x00bad")},
                    headers=admin_headers)  # fmt: skip
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "file"


def test_export_honours_filters_and_includes_current_salary(client, session, org, viewer_headers):
    make_employee(session, org, employee_number="A1", last_name="Alpha", salary=10_000_000)
    make_employee(session, org, employee_number="B1", last_name="=cmd()", country_code="GB",
                  currency_code="GBP", salary=8_000_050)  # fmt: skip
    make_employee(session, org, employee_number="C1", termination_date=date(2025, 1, 1))
    session.commit()

    r = client.get("/employees/export.csv?country_code=GB", headers=viewer_headers)

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 1
    assert rows[0]["employee_number"] == "B1"
    assert rows[0]["last_name"] == "'=cmd()"  # formula injection neutralized
    assert rows[0]["annual_salary"] == "80000.50"
    assert rows[0]["status"] == "active"


def test_export_round_trips_through_import(client, session, org, admin_headers):
    make_employee(session, org, employee_number="R1", email="r1@acme.example", salary=12_345_600)
    session.commit()
    exported = client.get("/employees/export.csv", headers=admin_headers).text

    # Re-import under new numbers/emails: export columns are a superset of import columns.
    reimport = exported.replace("R1", "R2").replace("r1@", "r2@")
    r = upload(client, admin_headers, reimport)

    assert r.status_code == 200, r.json()
    assert r.json()["imported"] == 1


def test_template_has_import_columns(client, viewer_headers):
    r = client.get("/employees/import-template.csv", headers=viewer_headers)
    assert r.text.splitlines()[0] == HEADER


def test_error_list_is_capped_but_count_is_complete(client, admin_headers):
    rows = [f"X{i},A,B,x{i}@acme.example,ZZ,USD,Engineering,E,L1,2024-01-01,1" for i in range(600)]
    r = upload(client, admin_headers, "\n".join([HEADER, *rows]))

    assert r.status_code == 422
    assert r.json()["error_count"] == 600
    assert len(r.json()["errors"]) == 500
