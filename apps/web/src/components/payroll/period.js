const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export function periodLabel(year, month) {
  return `${MONTHS[month - 1]} ${year}`;
}

/** Periods HR can run: next month first, then back two years. Matches the
 * API rule that a run may be at most one month ahead. */
export function selectablePeriods(today = new Date(), back = 24) {
  const out = [];
  let y = today.getFullYear();
  let m = today.getMonth() + 2; // next month, 1-based
  if (m === 13) {
    m = 1;
    y += 1;
  }
  for (let i = 0; i <= back; i++) {
    out.push({ year: y, month: m, label: periodLabel(y, m) });
    m -= 1;
    if (m === 0) {
      m = 12;
      y -= 1;
    }
  }
  return out;
}
