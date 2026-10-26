// Money arrives from the API as integers in minor units plus an ISO 4217 code
// (ADR 002). These helpers are the only place that knows about exponents.

const ZERO_DECIMAL = new Set(["JPY", "KRW"]);

export function exponentFor(currency) {
  return ZERO_DECIMAL.has(currency) ? 0 : 2;
}

export function toMajor(amountMinor, currency) {
  return amountMinor / 10 ** exponentFor(currency);
}

/** "$85,000" style, no cents: salaries are agreed in whole units. */
export function formatMoney(amountMinor, currency, { cents = false } = {}) {
  if (amountMinor === null || amountMinor === undefined) return "—";
  const digits = cents ? exponentFor(currency) : 0;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(toMajor(amountMinor, currency));
}

/** "$1.2M" for dashboard tiles and chart axes. */
export function formatCompact(amountMinor, currency = "USD", digits = 1) {
  if (amountMinor === null || amountMinor === undefined) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: digits,
  }).format(toMajor(amountMinor, currency));
}

/** Percentage change between two amounts, or null when there is no previous. */
export function percentChange(previous, current) {
  if (!previous) return null;
  return ((current - previous) / previous) * 100;
}

export function formatPercent(value) {
  if (value === null || value === undefined) return "";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}
