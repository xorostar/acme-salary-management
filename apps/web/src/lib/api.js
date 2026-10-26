// Thin client for the ACME Salary API. Every call goes through `request`,
// which attaches the bearer token and turns error bodies into ApiError.

import { toQueryString } from "@/lib/query";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(
  /\/$/,
  "",
);

const TOKEN_KEY = "acme.token";
const USER_KEY = "acme.user";

// Session storage keeps the token for the tab's lifetime only (ADR 007).
export const session = {
  get token() {
    try {
      return window.sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  get user() {
    try {
      return JSON.parse(window.sessionStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  },
  save(token, user) {
    try {
      window.sessionStorage.setItem(TOKEN_KEY, token);
      window.sessionStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch {
      /* storage unavailable: the user stays logged in until reload */
    }
  },
  clear() {
    try {
      window.sessionStorage.removeItem(TOKEN_KEY);
      window.sessionStorage.removeItem(USER_KEY);
    } catch {
      /* ignore */
    }
  },
};

export class ApiError extends Error {
  constructor(status, detail, fieldErrors = [], body = null) {
    super(detail || `Request failed (${status})`);
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.body = body;
  }

  /** {field: message} for showing errors next to form inputs. */
  get byField() {
    return Object.fromEntries(this.fieldErrors.map((e) => [e.field, e.message]));
  }
}

/**
 * Normalize both error shapes: ours ({detail, errors:[{field,message}]}) and
 * FastAPI's request validation ({detail:[{loc, msg}]}).
 */
export function parseError(status, body) {
  if (body && Array.isArray(body.detail)) {
    const errors = body.detail.map((d) => ({
      field: Array.isArray(d.loc) ? String(d.loc[d.loc.length - 1]) : "request",
      message: d.msg,
    }));
    return new ApiError(status, "Validation failed", errors, body);
  }
  const detail = body?.detail || (status === 0 ? "Cannot reach the server" : null);
  return new ApiError(status, detail, body?.errors || [], body);
}

let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export async function request(path, { method = "GET", body, query, raw = false, form } = {}) {
  const headers = {};
  const token = session.token;
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(`${API_URL}${path}${query ? toQueryString(query) : ""}`, {
      method,
      headers,
      body: payload,
    });
  } catch {
    throw parseError(0, null);
  }

  if (res.status === 401 && path !== "/auth/login") {
    session.clear();
    onUnauthorized();
  }
  if (raw && res.ok) return res;

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) throw parseError(res.status, data);
  return data;
}

/** Download an authenticated file (CSV export) via a blob URL. */
export async function download(path, query, fallbackName) {
  const res = await request(path, { query, raw: true });
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = match ? match[1] : fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  login: (email, password) => request("/auth/login", { method: "POST", body: { email, password } }),
  reference: () => request("/reference"),

  employees: (query) => request("/employees", { query }),
  employee: (id) => request(`/employees/${id}`),
  createEmployee: (body) => request("/employees", { method: "POST", body }),
  updateEmployee: (id, body) => request(`/employees/${id}`, { method: "PUT", body }),
  addSalaryEvent: (id, body) => request(`/employees/${id}/salary-events`, { method: "POST", body }),
  terminate: (id, body) => request(`/employees/${id}/terminate`, { method: "POST", body }),
  reactivate: (id, body) => request(`/employees/${id}/reactivate`, { method: "POST", body }),
  exportEmployees: (query) => download("/employees/export.csv", query, "employees.csv"),
  importTemplate: () => download("/employees/import-template.csv", null, "import-template.csv"),
  importEmployees: (file, dryRun) => {
    const form = new FormData();
    form.append("file", file);
    return request("/employees/import", { method: "POST", form, query: { dry_run: dryRun } });
  },

  overview: (query) => request("/analytics/overview", { query }),
  breakdown: (query) => request("/analytics/breakdown", { query }),
  matrix: (query) => request("/analytics/matrix", { query }),

  payrollRuns: () => request("/payroll-runs"),
  payrollRun: (id) => request(`/payroll-runs/${id}`),
  payrollLines: (id, query) => request(`/payroll-runs/${id}/lines`, { query }),
  createPayrollRun: (year, month) =>
    request("/payroll-runs", { method: "POST", body: { year, month } }),
  exportPayrollRun: (id) => download(`/payroll-runs/${id}/export.csv`, null, "payroll.csv"),
};
