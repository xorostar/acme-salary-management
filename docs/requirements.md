# Requirements: ACME Salary Management

**Persona:** HR Manager at ACME, a 10,000-employee organization operating in several countries.
**Problem:** Salary data lives in spreadsheets. Editing is tedious, history is lost, and answering "how do we pay people?" means manual pivot tables.

## Goal

Replace the spreadsheets with a web application where the HR manager can maintain employee salary records with a full change history, and answer compensation questions across countries, departments, and levels in one normalized currency.

## In scope

**Manage salary data**
- Employee directory: server-side paginated list with search, sort, and filters (country, department, level, status).
- Employee detail: profile, current compensation, and a dated salary history.
- Create and edit employees. Salary changes are recorded as dated events with a reason; the current salary is derived from history, never overwritten.
- Terminate and reactivate employees. Terminated staff stay in history but leave headcount and payroll totals by default.
- CSV import with whole-file validation and a row-level error report (all-or-nothing), plus CSV export of any filtered view.

**Answer questions about pay**
- Dashboard: headcount, total annual payroll, mean and median salary, sliceable by country, department, and level.
- Distribution view: percentiles (p10, p25, p50, p75, p90) and histogram per group.
- All cross-country figures are converted to USD using a seeded, versioned exchange-rate table so every report is reproducible.

**Payroll run (lightweight)**
- Generate a monthly payroll run: a frozen snapshot of what each active employee is owed for the period, in local currency, with per-country totals. No payments are made; the run is a reviewable, exportable record.

**Access control (basic)**
- Email and password login with signed session tokens.
- Two roles: `hr_admin` (full write access, import, payroll runs) and `hr_viewer` (read-only access to directory and analytics).

**Non-functional**
- Correct money handling: integer minor units, ISO 4217 currency codes, zero-decimal currencies respected.
- 10,000-row operations stay responsive: pagination, filtering, sorting, and aggregates run in SQL on indexed columns.
- Deterministic seed of 10,000 realistic employees so demos and tests are reproducible.
- Fast, deterministic unit tests on domain logic and API behavior.

## Deliberately out of scope

| Excluded | Reason |
|---|---|
| Multi-tenancy (several organizations) | One customer today. The schema carries an `organization_id` on every tenant-owned table and all queries are scoped through it, so adding tenants later is additive, not a rewrite. |
| Payment provider integration, bank files, tax, benefits, bonuses, equity | The brief is about salary data, not payment execution. A payroll run records what is owed; paying it is a separate system with its own compliance burden. |
| Live exchange rates | Live rates make reports non-reproducible and tests flaky. A seeded rate table with an `effective_date` gives the same answer every time and can be refreshed by a job later. |
| Approval workflows, notifications, audit UI | Valuable, but the single persona is the approver. Every change is already stored with actor and timestamp, so an audit screen can be added without schema changes. |
| Employee self-service, manager views, SSO, password reset | Only the HR persona is in scope. Basic roles exist to show the boundary; identity federation is an integration concern, not a product one. |
| Granular permissions, field-level masking | Two roles cover the stated use. A permission matrix would add surface area with no user asking for it. |

## Success criteria

- An HR manager can find any employee in under three clicks, change a salary with a reason, and see the change in history.
- The dashboard answers "median salary by country in USD" without exporting anything.
- A 10,000-row CSV import either succeeds completely or reports every bad row.
- The test suite runs in seconds with no network and no real clock.

## Note added after the build (26 Oct 2026)

This page was written before any code and is kept as written. Where the build differs:

- **Percentiles are computed in Python, not SQL.** Salaries must be converted to USD per
  currency first, and SQLite has no percentile function. Filtering, sorting, paging and
  counting still run in SQL. See [performance.md](performance.md).
- **Audit data.** Salary changes record who made them and when. Edits to employee details
  record when (`updated_at`, `version`) but not who. An audit screen would need an
  `updated_by` column for those.
- **Decisions made while building** are recorded as ADR 008 (payroll run rules: no
  proration, one run per month) and ADR 009 (CSV import creates new hires only).
