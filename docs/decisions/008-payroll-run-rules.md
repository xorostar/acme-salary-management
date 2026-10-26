# ADR 008: Payroll run rules

**Status:** Accepted

## Context

The requirements promise a lightweight monthly payroll run: a frozen, reviewable record of
what each employee is owed, with no payments. Several rules had to be chosen when building
it.

## Decision

| Question | Rule |
|---|---|
| Who is included? | Everyone employed on the **last day** of the month: hired on or before it, and not terminated on or before it. |
| Which salary? | The annual salary in force on that day (ADR 003), divided by 12, rounded half-up once. |
| Which rate? | The planning rate in force on that day (ADR 006). Stored on each line. |
| A currency has no rate? | The whole run is refused with a field error. Nothing is guessed. |
| Run twice for one month? | Rejected (409). A database unique constraint backs the check against races. |
| Future months? | At most one month ahead, so next month can be prepared but not years ahead. |
| Can a run change? | No. Lines copy name, department, amounts and rate. Later edits never alter it. |

## Reasoning

- "Employed on the last day" is one date to reason about and matches how a monthly salary
  is usually paid in arrears.
- Copying values instead of referencing them is what makes a run an audit record.
- Refusing on a missing rate is safer than excluding people silently from a payroll total.

## Trade-offs accepted

- **No proration.** Someone hired on the 20th or leaving on the 10th gets a full month or
  none. Proration rules differ by country and contract; they belong with a real payroll
  provider. The rule is stated in the UI next to the Run button.
- **No delete or re-run.** A mistaken run stays visible. A future "void and re-run" would add
  a status, not remove history.
- **Salaries are annual only.** Countries paid 13 or 14 times a year would need a pay
  frequency column, which is additive.
