# ADR 003: Salary history as append-only events

**Status:** Accepted

## Context

The spreadsheet workflow loses history: a salary cell gets overwritten and nobody knows what it was before, when it changed, or why. The HR manager needs to answer "what was this person paid last March?" and "who changed this?".

## Decision

`employees` has no salary column. Salary lives only in `salary_events`:

| column | meaning |
|---|---|
| `annual_amount_minor`, `currency_code` | the new annual salary |
| `effective_date` | the date the new salary applies from |
| `reason` | free text, required (hire, promotion, annual review, correction, market adjustment) |
| `created_by_user_id`, `created_at` | who recorded it and when |

The **current salary** is the event with the greatest `effective_date` that is on or before the reference date (injected, defaults to today). Events are never updated or deleted; a mistake is corrected by a new event with reason "correction".

## Rules enforced in `domain/salary.py`

- Amount must be a positive integer.
- Currency must match the employee's currency. Changing currency is a relocation, which is an employee edit, not a salary change.
- `effective_date` must be on or after `hire_date`.
- Two events on the same `effective_date` for one employee are rejected; the HR manager must pick the date or correct the earlier one.
- Future-dated events are allowed so raises can be entered ahead of time. They do not affect "current" until their date arrives.
- An employee must have at least one event (their starting salary) created at hire.

## Reasoning

- Append-only data is trivially auditable and never loses information.
- Deriving "current" from a reference date makes the logic testable without a real clock and makes historical questions free.
- The index on `(employee_id, effective_date)` makes the "latest on or before date" lookup one index seek per employee.

## Trade-offs accepted

- The employee list needs a correlated subquery to show current salary. Measured and documented in `docs/performance.md`.
- Pay frequency is not modelled. Salaries are annual; the payroll run divides by twelve. Countries with different pay cadences would need a `pay_frequency` column later, which is additive.
