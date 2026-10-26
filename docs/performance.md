# Performance

The brief's scale is 10,000 employees. The goal was not raw speed but that every screen
an HR manager uses feels instant on that data, on a single small server, with numbers
measured rather than assumed.

## How it was measured

- Data: the deterministic seed. 10,000 employees, 43,024 salary events, nine countries.
- Server: uvicorn, one process, SQLite file in WAL mode. Laptop with an 8-thread Intel CPU.
- Tool: [`apps/api/scripts/benchmark.py`](../apps/api/scripts/benchmark.py) logs in and
  times each request over real HTTP (routing, auth, validation, serialization). It reports
  the median of 15 runs after one warm-up.

```bash
cd apps/api
uvicorn app.main:app --port 8000          # seeded database
python scripts/benchmark.py http://127.0.0.1:8000
```

## Results

| Request | Median (ms) |
|---|---|
| Directory, page 1 | 7 |
| Directory, page 200 | 11 |
| Directory, sorted by current salary | 21 |
| Directory, free-text search | 53 |
| Directory, country + level filter | 8 |
| Employee detail with history | 4 |
| Analytics overview (all 9,321 active) | 78 |
| Breakdown by country | 86 |
| Level x country median matrix | 67 |
| CSV export, all active employees | 435 |

| Bulk operation (10,000 rows) | Time |
|---|---|
| Seed (generate + insert) | 1.4 to 2.1 s |
| CSV import, validate only | 0.4 s |
| CSV import, validate + insert | 3.2 s |
| Payroll run (9,300 lines) | under 1.5 s end to end in the browser |

Timings on a busy machine were two to four times higher. The ratios between rows held.

## Decisions, and what measuring changed

**1. Current salary is derived, with one index seek per employee.** Salary lives only in
append-only `salary_events` (ADR 003). "Current" is the latest event on or before the
reference date, read through the `(employee_id, effective_date)` index with a correlated
subquery.

**2. Directory paging uses a deferred join.** The first version computed the current salary
in the same query as the page. SQLite evaluates select-list subqueries for every row it
skips with `OFFSET`, so page 200 paid for 5,000 salary lookups.
The fix selects the page of IDs using only employee columns, then fetches rows and salaries
for those 25 IDs. Page 200 went from about 315 ms to about 34 ms, measured back to back on
the same machine. Sorting by salary still needs the subquery for ordering, which is why that
row is slower.

**3. A "faster" query that was slower.** For analytics I replaced the correlated subquery
with a grouped join (`MAX(effective_date) GROUP BY employee_id`, then join back). That is
usually faster in PostgreSQL. On SQLite it measured about twice as slow: 100 ms vs 38 ms
minimum, 226 ms vs 78 ms median. The query plan showed SQLite building an automatic index for
the grouped subquery on every call. I reverted it and documented the reason in the
repository code.

**4. Currency conversion in integers.** Analytics converts about 9,300 salaries to USD per
request. `RateConverter` turns each rate into an exact fraction once, so each conversion is
one multiply and one floor-divide. A test checks it gives the same results as the Decimal
reference implementation on 24,000 values, including half-cent ties.

**5. Percentiles in Python, not SQL.** SQLite has no percentile function, and amounts must be
converted per currency first. After conversion, sorting 9,300 integers and reading five
percentiles takes about 1 ms. A window-function query would be harder to read and to test
against hand-computed values.

**6. Bulk paths use SQLAlchemy Core.** Seed, import, and payroll lines insert in batches. The
import checks for existing employee numbers and emails in chunks of 500 to stay under
SQLite's bound-parameter limit.

**7. Validation finds every error before any write.** An import with 20,000 problems
returns the first 500 and the total count. The browser does not receive a megabyte of
JSON.

**8. Frontend.** The search box is debounced (300 ms). Responses to superseded requests are
dropped, so fast typing never shows stale rows. The previous page stays on screen, dimmed,
while the next one loads. Tables page on the server and never hold 10,000 rows in the
browser.

## Indexes

| Index | Serves |
|---|---|
| `salary_events (employee_id, effective_date)` | current salary, history, uniqueness per date |
| `employees (organization_id, country_code / department / level)` | directory filters, analytics filters |
| `employees (organization_id, last_name, first_name)` | default directory sort |
| `employees (organization_id, termination_date)` | the active / terminated filter |
| `payroll_lines (payroll_run_id, country_code)` | per-country totals and line filter |

## Where it would stop scaling, and what to do then

| Pressure | First response |
|---|---|
| Analytics at about 100k employees (~1 s) | Cache per `(organization, as_of, data version)`; every write bumps the version. |
| Many concurrent writers | Move to PostgreSQL. SQLAlchemy keeps it a connection string change plus `percentile_cont`. |
| Search across very large orgs | SQLite FTS5 or PostgreSQL trigram index instead of `LIKE '%term%'`. |
| Current-salary lookups dominating | Denormalize a `current_salary_event_id` on employees, maintained in the same transaction as the event insert. Not done now because it is a second source of truth to keep in sync. |
