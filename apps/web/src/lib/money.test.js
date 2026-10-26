import { describe, expect, it } from "vitest";

import {
  exponentFor,
  formatCompact,
  formatMoney,
  formatPercent,
  percentChange,
  toMajor,
} from "@/lib/money";

describe("money", () => {
  it("knows zero-decimal currencies", () => {
    expect(exponentFor("JPY")).toBe(0);
    expect(exponentFor("USD")).toBe(2);
    expect(toMajor(9_000_000, "JPY")).toBe(9_000_000);
    expect(toMajor(8_500_050, "GBP")).toBe(85_000.5);
  });

  it("formats whole units by default and cents on request", () => {
    expect(formatMoney(8_500_050, "USD")).toBe("$85,001");
    expect(formatMoney(8_500_050, "USD", { cents: true })).toBe("$85,000.50");
    expect(formatMoney(9_000_000, "JPY", { cents: true })).toBe("¥9,000,000");
  });

  it("shows a dash for missing amounts", () => {
    expect(formatMoney(null, "USD")).toBe("—");
    expect(formatCompact(undefined)).toBe("—");
  });

  it("formats compact USD for tiles", () => {
    expect(formatCompact(123_456_789_00)).toBe("$123.5M");
  });

  it("computes and formats change", () => {
    expect(percentChange(100, 110)).toBeCloseTo(10);
    expect(percentChange(0, 110)).toBeNull();
    expect(formatPercent(4.25)).toBe("+4.3%");
    expect(formatPercent(-2)).toBe("-2.0%");
    expect(formatPercent(null)).toBe("");
  });
});
