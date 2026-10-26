import { afterEach, describe, expect, it, vi } from "vitest";

import { api, parseError, session } from "@/lib/api";

describe("parseError", () => {
  it("maps our field errors", () => {
    const err = parseError(422, {
      detail: "Validation failed",
      errors: [{ field: "email", message: "is already in use" }],
    });
    expect(err.status).toBe(422);
    expect(err.byField).toEqual({ email: "is already in use" });
  });

  it("maps FastAPI request validation errors to the last loc segment", () => {
    const err = parseError(422, { detail: [{ loc: ["body", "hire_date"], msg: "Invalid date" }] });
    expect(err.byField).toEqual({ hire_date: "Invalid date" });
  });

  it("explains a network failure", () => {
    expect(parseError(0, null).message).toBe("Cannot reach the server");
  });
});

describe("request", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    session.clear();
  });

  it("sends the bearer token and drops empty query params", async () => {
    session.save("tok", { email: "a" });
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [] })));
    vi.stubGlobal("fetch", fetchMock);

    await api.employees({ q: "", country_code: "GB", page: 2 });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/employees\?country_code=GB&page=2$/);
    expect(init.headers.Authorization).toBe("Bearer tok");
  });

  it("throws ApiError with the server's message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Employee 9 not found" }), { status: 404 }),
      ),
    );
    await expect(api.employee(9)).rejects.toMatchObject({
      status: 404,
      message: "Employee 9 not found",
    });
  });

  it("clears the session on 401", async () => {
    session.save("tok", { email: "a" });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "expired" }), { status: 401 })),
    );
    await expect(api.reference()).rejects.toMatchObject({ status: 401 });
    expect(session.token).toBeNull();
  });
});
