"use client";

import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { pageCount } from "@/lib/query";

export function Pagination({ page, pageSize, total, onPage, onPageSize, sizes = [25, 50, 100] }) {
  const pages = pageCount(total, pageSize);
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  return (
    <nav
      className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm"
      aria-label="Pagination"
    >
      <p className="text-muted-foreground tabular-nums">
        {first.toLocaleString("en-US")}–{last.toLocaleString("en-US")} of{" "}
        {total.toLocaleString("en-US")}
      </p>
      <div className="flex items-center gap-2">
        {onPageSize && (
          <NativeSelect
            aria-label="Rows per page"
            value={pageSize}
            onChange={(e) => onPageSize(Number(e.target.value))}
            className="w-24"
          >
            {sizes.map((s) => (
              <option key={s} value={s}>
                {s} / page
              </option>
            ))}
          </NativeSelect>
        )}
        <Button
          variant="outline"
          size="icon-sm"
          aria-label="Previous page"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          <ChevronLeftIcon />
        </Button>
        <span className="tabular-nums">
          Page {page} of {pages}
        </span>
        <Button
          variant="outline"
          size="icon-sm"
          aria-label="Next page"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
        >
          <ChevronRightIcon />
        </Button>
      </div>
    </nav>
  );
}
