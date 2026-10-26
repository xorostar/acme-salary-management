"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

// Reference data (countries, departments, levels) changes only on deploy, so
// one request per page load is enough. A failed load is retried next time.
let cached = null;

export function useReference() {
  const [data, setData] = useState(cached?.value ?? null);

  useEffect(() => {
    if (cached?.value) return;
    if (!cached) {
      cached = { promise: api.reference() };
      cached.promise.then(
        (value) => (cached.value = value),
        () => (cached = null),
      );
    }
    let alive = true;
    cached.promise.then((value) => alive && setData(value)).catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  return data;
}

export function countryName(reference, code) {
  return reference?.countries.find((c) => c.code === code)?.name ?? code;
}

export function currencyForCountry(reference, code) {
  return reference?.countries.find((c) => c.code === code)?.currency_code ?? "";
}
