# ADR 006: Seeded, dated exchange rates instead of a live feed

**Status:** Accepted

## Context

Cross-country analytics need a common currency. The organization's base currency is USD. Rates could come from a live API or from a table the HR team controls.

## Decision

An `exchange_rates` table with `(currency_code, rate_to_usd, effective_date)`. The seed loads one rate per currency. Conversions use the latest rate on or before the reference date. No live feed.

## Reasoning

- **Reproducibility.** A report run twice must give the same number. A live rate changes every minute.
- **Testability.** Tests assert exact converted amounts against hand-computed values. A network call would make them slow and flaky.
- **HR reality.** Compensation teams fix a "planning rate" for a period and use it consistently. A dated table models that directly.
- **Future-proof.** A nightly job can insert new rows without changing any reading code.

## Trade-offs accepted

- Rates in the seed are approximate and will drift from the market. They are labelled as planning rates in the UI.
- No UI to edit rates in this version. Rates change by migration or script.
