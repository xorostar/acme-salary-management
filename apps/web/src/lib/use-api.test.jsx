import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useApi } from "@/lib/use-api";

function deferred() {
  let resolve;
  const promise = new Promise((r) => (resolve = r));
  return { promise, resolve };
}

describe("useApi", () => {
  it("ignores a slow response that was superseded by a newer request", async () => {
    const slow = deferred();
    const fast = deferred();
    const calls = { a: slow.promise, b: fast.promise };

    const { result, rerender } = renderHook(({ key }) => useApi(() => calls[key], key), {
      initialProps: { key: "a" },
    });
    rerender({ key: "b" });

    await act(async () => fast.resolve("results for b"));
    await act(async () => slow.resolve("stale results for a"));

    expect(result.current.data).toBe("results for b");
    expect(result.current.loading).toBe(false);
  });

  it("keeps previous data visible while the next request loads", async () => {
    const first = deferred();
    const second = deferred();
    const calls = { 1: first.promise, 2: second.promise };
    const { result, rerender } = renderHook(({ page }) => useApi(() => calls[page], page), {
      initialProps: { page: 1 },
    });
    await act(async () => first.resolve("page 1"));

    rerender({ page: 2 });

    expect(result.current.data).toBe("page 1");
    expect(result.current.loading).toBe(true);
  });

  it("exposes errors and recovers on reload", async () => {
    let attempt = 0;
    const { result } = renderHook(() =>
      useApi(() => (++attempt === 1 ? Promise.reject(new Error("boom")) : Promise.resolve("ok")), "k"),
    );
    await waitFor(() => expect(result.current.error?.message).toBe("boom"));

    act(() => result.current.reload());

    await waitFor(() => expect(result.current.data).toBe("ok"));
    expect(result.current.error).toBeNull();
  });
});
