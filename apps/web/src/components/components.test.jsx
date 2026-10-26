import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { withChanges } from "@/components/employees/salary-history";
import { ImportErrors } from "@/components/employees/import-employees";
import { SortHeader } from "@/components/employees/employee-table";
import { selectablePeriods } from "@/components/payroll/period";

describe("SortHeader", () => {
  const column = { key: "hire_date", label: "Hired" };

  function renderHeader(props) {
    return render(
      <table>
        <thead>
          <tr>
            <SortHeader column={column} {...props} />
          </tr>
        </thead>
      </table>,
    );
  }

  it("announces the current sort to screen readers", () => {
    renderHeader({ sort: "hire_date", order: "desc", onSort: () => {} });
    expect(screen.getByRole("columnheader")).toHaveAttribute("aria-sort", "descending");
  });

  it("reports clicks with its column key", async () => {
    const onSort = vi.fn();
    renderHeader({ sort: "last_name", order: "asc", onSort });
    expect(screen.getByRole("columnheader")).toHaveAttribute("aria-sort", "none");

    await userEvent.click(screen.getByRole("button", { name: /hired/i }));

    expect(onSort).toHaveBeenCalledWith("hire_date");
  });
});

describe("ImportErrors", () => {
  it("lists each row problem and says nothing was imported", () => {
    render(
      <ImportErrors
        result={{
          error_count: 2,
          errors: [
            { row: 3, field: "country_code", message: "unsupported country 'ZZ'" },
            { row: 7, field: "email", message: "duplicate of row 2" },
          ],
        }}
      />,
    );
    expect(screen.getByText(/2 problems found\. Nothing was imported\./)).toBeInTheDocument();
    expect(screen.getByText("duplicate of row 2")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(3);
  });

  it("says when the list is truncated", () => {
    render(
      <ImportErrors
        result={{ error_count: 600, errors: [{ row: 2, field: "x", message: "bad" }] }}
      />,
    );
    expect(screen.getByText(/Showing the first 1\./)).toBeInTheDocument();
  });
});

describe("withChanges", () => {
  it("computes change against the previous entry in the same currency only", () => {
    const rows = withChanges([
      { id: 3, effective_date: "2025-01-01", annual_amount_minor: 4_000_000, currency_code: "GBP" },
      { id: 1, effective_date: "2022-01-01", annual_amount_minor: 100, currency_code: "USD" },
      { id: 2, effective_date: "2023-01-01", annual_amount_minor: 110, currency_code: "USD" },
    ]);
    expect(rows.map((r) => r.id)).toEqual([1, 2, 3]);
    expect(rows[0].change).toBeNull();
    expect(rows[1].change).toBeCloseTo(10);
    expect(rows[2].change).toBeNull(); // relocation: USD -> GBP is not a raise
  });
});

describe("selectablePeriods", () => {
  it("offers next month first, across the year end", () => {
    const periods = selectablePeriods(new Date(2025, 11, 15), 2);
    expect(periods.map((p) => p.label)).toEqual([
      "January 2026",
      "December 2025",
      "November 2025",
    ]);
  });
});
