// URL search params are the single source of truth for list and dashboard
// state, so views are shareable and the back button works.

export const DIRECTORY_DEFAULTS = {
  q: "",
  country_code: "",
  department: "",
  level: "",
  status: "active",
  sort: "last_name",
  order: "asc",
  page: 1,
  page_size: 25,
};

const SORTABLE = new Set([
  "last_name",
  "employee_number",
  "hire_date",
  "department",
  "country_code",
  "level",
  "current_salary",
]);
const STATUSES = new Set(["active", "terminated", "all"]);
const PAGE_SIZES = [25, 50, 100];

function positiveInt(value, fallback) {
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

/** Read directory state from URLSearchParams, ignoring anything invalid. */
export function parseDirectoryState(searchParams) {
  const get = (k) => searchParams.get(k) ?? "";
  const sort = get("sort");
  const pageSize = positiveInt(get("page_size"), DIRECTORY_DEFAULTS.page_size);
  return {
    q: get("q"),
    country_code: get("country_code"),
    department: get("department"),
    level: get("level"),
    status: STATUSES.has(get("status")) ? get("status") : DIRECTORY_DEFAULTS.status,
    sort: SORTABLE.has(sort) ? sort : DIRECTORY_DEFAULTS.sort,
    order: get("order") === "desc" ? "desc" : "asc",
    page: positiveInt(get("page"), 1),
    page_size: PAGE_SIZES.includes(pageSize) ? pageSize : DIRECTORY_DEFAULTS.page_size,
  };
}

/** Build a query string, dropping empty values and values equal to defaults. */
export function toQueryString(params, defaults = {}) {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === "" || value === null || value === undefined) continue;
    if (defaults[key] !== undefined && String(defaults[key]) === String(value)) continue;
    sp.set(key, String(value));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/**
 * Next state after a change. Changing anything other than the page resets to
 * page 1, so a new filter never lands on an empty page 37.
 */
export function updateState(state, changes) {
  const next = { ...state, ...changes };
  if (!("page" in changes)) next.page = 1;
  return next;
}

/** Clicking a column: same column flips direction, new column starts ascending
 * (salary starts descending, since "who is paid most" is the usual question). */
export function nextSort(state, column) {
  if (state.sort === column) {
    return { sort: column, order: state.order === "asc" ? "desc" : "asc" };
  }
  return { sort: column, order: column === "current_salary" ? "desc" : "asc" };
}

export function pageCount(total, pageSize) {
  return Math.max(1, Math.ceil(total / pageSize));
}

export const ANALYTICS_FILTER_KEYS = ["country_code", "department", "level"];

export function parseAnalyticsFilters(searchParams) {
  return Object.fromEntries(ANALYTICS_FILTER_KEYS.map((k) => [k, searchParams.get(k) ?? ""]));
}
