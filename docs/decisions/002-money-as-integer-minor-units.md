# ADR 002: Money as integer minor units with an explicit currency

**Status:** Accepted

## Context

Salaries are stored in nine currencies, including JPY which has no fractional unit. Reports convert everything to USD. Rounding errors in salary data are unacceptable.

## Decision

- Every amount is stored as an integer in the currency's minor unit (`annual_amount_minor`) next to an ISO 4217 `currency_code`.
- The minor-unit exponent per currency lives in `domain/money.py` (JPY and KRW are 0, everything else here is 2).
- Exchange rates are stored as decimal strings and parsed with `decimal.Decimal`. Conversion rounds half-up to the target currency's exponent, once, at the end.
- Floats are never used for money. The API returns amounts as integers plus a currency, and the UI formats them with `Intl.NumberFormat`.

## Reasoning

- Integers add and compare exactly. `0.1 + 0.2` problems disappear.
- Carrying the currency on each row means a mixed-currency sum is a bug the code can detect instead of silently producing nonsense.
- A per-currency exponent table prevents the classic "divide yen by 100" error.

## Trade-offs accepted

- Callers must know the exponent to display a value. A single `format_money` helper and the API's `currency_code` field keep this contained.
- Means and percentiles are computed on integer minor units after conversion to USD, then rounded half-up to a whole minor unit. Sub-unit precision on an aggregate is not meaningful for salaries.
