from app.domain.csv_io import IMPORT_COLUMNS, import_keys, parse_import, safe_cell, write_csv

HEADER = ",".join(IMPORT_COLUMNS)
GOOD = "E1,Ada,Lovelace,ada@acme.example,GB,GBP,Engineering,Engineer,L3,2024-01-15,65000.50"
GOOD2 = "E2,Alan,Turing,alan@acme.example,JP,JPY,Engineering,Engineer,L4,2023-05-01,9000000"


def csv_text(*rows: str, header: str = HEADER) -> str:
    return "\n".join([header, *rows]) + "\n"


def test_valid_file_parses_every_row_with_minor_units():
    result = parse_import(csv_text(GOOD, GOOD2))

    assert result.errors == []
    assert [r.annual_amount_minor for r in result.rows] == [6_500_050, 9_000_000]
    assert result.rows[0].employee.email == "ada@acme.example"


def test_values_are_normalized():
    row = " e1 ,Ada,Lovelace, ADA@ACME.example ,gb,gbp,Engineering,Engineer,l3,2024-01-15,1"
    (parsed,) = parse_import(csv_text(row)).rows
    assert parsed.employee.employee_number == "E1"
    assert parsed.employee.country_code == "GB"
    assert parsed.employee.level == "L3"


def test_excel_byte_order_mark_is_ignored():
    assert parse_import("﻿" + csv_text(GOOD)).errors == []


def test_missing_columns_are_reported_once():
    result = parse_import(csv_text("x,y", header="employee_number,first_name"))
    assert len(result.errors) == 1
    assert result.errors[0].field == "header"
    assert "annual_salary" in result.errors[0].message


def test_every_error_is_reported_with_its_spreadsheet_row():
    bad_country = GOOD.replace(",GB,GBP,", ",XX,GBP,")
    bad_date = GOOD2.replace("2023-05-01", "01/05/2023")
    result = parse_import(csv_text(GOOD, bad_country.replace("E1", "E3")
                                   .replace("ada@", "x@"), bad_date))  # fmt: skip

    assert result.rows == []  # caller must not import a partially valid file
    assert {(e.row, e.field) for e in result.errors} == {(3, "country_code"), (4, "hire_date")}


def test_bad_date_still_reports_other_field_errors():
    row = GOOD.replace("2024-01-15", "soon").replace("Engineering", "Nope")
    fields = {e.field for e in parse_import(csv_text(row)).errors}
    assert fields == {"hire_date", "department"}


def test_fractional_yen_is_rejected():
    result = parse_import(csv_text(GOOD2.replace("9000000", "9000000.5")))
    assert [(e.field, e.row) for e in result.errors] == [("annual_salary", 2)]


def test_non_positive_salary_is_rejected():
    result = parse_import(csv_text(GOOD.replace("65000.50", "0")))
    assert result.errors[0].field == "annual_salary"


def test_duplicates_within_file_point_to_first_row():
    dup = GOOD.replace("ada@", "other@")
    result = parse_import(csv_text(GOOD, dup))
    assert [(e.row, e.field, e.message) for e in result.errors] == [
        (3, "employee_number", "duplicate of row 2")
    ]


def test_conflicts_with_existing_employees():
    result = parse_import(
        csv_text(GOOD), existing_numbers={"E1"}, existing_emails={"ada@acme.example"}
    )
    assert {e.field for e in result.errors} == {"employee_number", "email"}


def test_blank_lines_are_skipped_but_empty_file_is_an_error():
    assert parse_import(csv_text(GOOD, ",,,,,,,,,,")).errors == []
    assert parse_import(csv_text()).errors[0].message == "contains no data rows"


def test_import_keys_normalizes_for_lookup():
    numbers, emails = import_keys(csv_text(GOOD.replace("E1", "e1").replace("ada@", "ADA@")))
    assert numbers == ["E1"]
    assert emails == ["ada@acme.example"]


def test_formula_injection_is_neutralized():
    assert safe_cell("=HYPERLINK(evil)") == "'=HYPERLINK(evil)"
    assert safe_cell("@SUM(A1)") == "'@SUM(A1)"
    assert safe_cell("Smith") == "Smith"
    assert safe_cell(None) == ""


def test_write_csv_streams_header_and_rows():
    text = "".join(write_csv(([i, "x"] for i in range(1200)), ["n", "v"]))
    lines = text.split("\r\n")
    assert lines[0] == "n,v"
    assert lines[1200] == "1199,x"
