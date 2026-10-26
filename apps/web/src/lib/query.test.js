import { describe, expect, it } from "vitest";

import {
  DIRECTORY_DEFAULTS,
  nextSort,
  pageCount,
  parseDirectoryState,
  toQueryString,
  updateState,
} from "@/lib/query";

const params = (s) => new URLSearchParams(s);

describe("directory URL state", () => {
  it("falls back to defaults for an empty URL", () => {
    expect(parseDirectoryState(params(""))).toEqual(DIRECTORY_DEFAULTS);
  });

  it("ignores invalid values instead of sending them to the API", () => {
    const s = parseDirectoryState(params("sort=password&status=x&page=-3&page_size=7&order=up"));
    expect(s.sort).toBe("last_name");
    expect(s.status).toBe("active");
    expect(s.page).toBe(1);
    expect(s.page_size).toBe(25);
    expect(s.order).toBe("asc");
  });

  it("round-trips through a query string that omits defaults", () => {
    const state = { ...DIRECTORY_DEFAULTS, q: "ada", country_code: "GB", page: 3 };
    const qs = toQueryString(state, DIRECTORY_DEFAULTS);
    expect(qs).toBe("?q=ada&country_code=GB&page=3");
    expect(parseDirectoryState(params(qs.slice(1)))).toEqual(state);
  });

  it("returns an empty string when everything is default", () => {
    expect(toQueryString(DIRECTORY_DEFAULTS, DIRECTORY_DEFAULTS)).toBe("");
  });

  it("resets to page 1 when a filter changes, but not when paging", () => {
    const state = { ...DIRECTORY_DEFAULTS, page: 5 };
    expect(updateState(state, { level: "L3" }).page).toBe(1);
    expect(updateState(state, { page: 6 }).page).toBe(6);
  });

  it("toggles sort direction on the same column", () => {
    const state = { ...DIRECTORY_DEFAULTS, sort: "hire_date", order: "asc" };
    expect(nextSort(state, "hire_date")).toEqual({ sort: "hire_date", order: "desc" });
    expect(nextSort(state, "level")).toEqual({ sort: "level", order: "asc" });
  });

  it("starts salary sort with the highest paid", () => {
    expect(nextSort(DIRECTORY_DEFAULTS, "current_salary").order).toBe("desc");
  });

  it("always has at least one page", () => {
    expect(pageCount(0, 25)).toBe(1);
    expect(pageCount(51, 25)).toBe(3);
  });
});
