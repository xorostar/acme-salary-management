# ADR 009: CSV import creates new hires, all or nothing

**Status:** Accepted

## Context

HR currently lives in spreadsheets, so getting data in and out by CSV is the bridge from
the old workflow. An import that half-succeeds is worse than none: the HR manager cannot
tell which rows landed.

## Decision

- Import **creates new employees only**, each with a starting salary effective on the hire
  date (recorded as made by the importing user).
- **All or nothing.** Every row is validated with the same domain rules as the API,
  including duplicates within the file and against existing employees. Any error rejects the
  whole file. The parser returns no rows when any row fails, so no caller can import half a
  file by accident.
- Every problem is reported with its **spreadsheet row number**. The UI first runs a **dry
  run** ("Check file") and enables "Import" only when the file is clean.
- **Export** produces a superset of the import columns, so an exported file can be edited
  and re-imported under new numbers.
- Limits: 4 MB (below the hosting platform's 4.5 MB request limit), 20,000 rows, UTF-8 (a BOM from Excel is accepted), and at most 500 errors
  returned with the total count.
- Export neutralizes spreadsheet formula injection: a cell starting with `= + - @` is
  prefixed with an apostrophe.

## Reasoning

- New hires are the common bulk case: an onboarding batch arriving as a spreadsheet.
- Validating everything before writing matches the requirement's success criterion. A
  10,000-row import "either succeeds completely or reports every bad row."

## Trade-offs accepted

- **No bulk updates.** An annual review applied as a CSV of raises is the obvious next
  feature. It needs different rules: match on employee number, an effective date per row,
  and a preview of changes. It was left out to keep this path simple and safe.
- Import runs in the request (about 3 s for 10,000 rows). A background job would be needed
  for much larger files.
