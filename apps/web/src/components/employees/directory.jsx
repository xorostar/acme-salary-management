"use client";

import { DownloadIcon, PlusIcon, SearchIcon, UploadIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ErrorState, LoadingRows, PageHeader } from "@/components/common";
import { EmployeeTable } from "@/components/employees/employee-table";
import { Pagination } from "@/components/employees/pagination";
import { OrgFilters } from "@/components/filters";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  DIRECTORY_DEFAULTS,
  nextSort,
  parseDirectoryState,
  toQueryString,
  updateState,
} from "@/lib/query";
import { useReference } from "@/lib/reference";
import { useApi, useDebounced } from "@/lib/use-api";

const STATUS_TABS = [
  ["active", "Active"],
  ["terminated", "Terminated"],
  ["all", "All"],
];

export function Directory() {
  const { isAdmin } = useAuth();
  const reference = useReference();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const state = parseDirectoryState(searchParams);
  const queryKey = toQueryString(state, DIRECTORY_DEFAULTS);

  const navigate = (changes) =>
    router.replace(`${pathname}${toQueryString(updateState(state, changes), DIRECTORY_DEFAULTS)}`, {
      scroll: false,
    });

  // The search box is local state so typing feels instant; the URL (and the
  // request) follow 300ms after the user stops typing.
  const [search, setSearch] = useState(state.q);
  const debounced = useDebounced(search);
  useEffect(() => {
    if (debounced !== state.q) navigate({ q: debounced });
    // navigate is recreated every render; only the debounced value matters here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  const { data, error, loading, reload } = useApi(() => api.employees(state), queryKey);
  const [exporting, setExporting] = useState(false);

  async function exportCsv() {
    setExporting(true);
    try {
      const { page: _p, page_size: _s, ...filters } = state;
      await api.exportEmployees(filters);
    } catch (e) {
      toast.error(`Export failed: ${e.message}`);
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Employees"
        description={
          data ? `${data.total.toLocaleString("en-US")} matching employees` : "Loading directory…"
        }
        actions={
          <>
            <Button variant="outline" onClick={exportCsv} disabled={exporting}>
              <DownloadIcon /> {exporting ? "Exporting…" : "Export CSV"}
            </Button>
            {isAdmin && (
              <>
                <Link href="/employees/import" className={buttonVariants({ variant: "outline" })}>
                  <UploadIcon /> Import CSV
                </Link>
                <Link href="/employees/new" className={buttonVariants()}>
                  <PlusIcon /> Add employee
                </Link>
              </>
            )}
          </>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-64">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            aria-label="Search by name, email or employee number"
            placeholder="Name, email or number"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        <OrgFilters reference={reference} value={state} onChange={navigate} />
        <div className="flex rounded-lg border p-0.5 sm:ml-auto" role="group" aria-label="Status">
          {STATUS_TABS.map(([value, label]) => (
            <Button
              key={value}
              size="sm"
              variant={state.status === value ? "secondary" : "ghost"}
              aria-pressed={state.status === value}
              onClick={() => navigate({ status: value })}
            >
              {label}
            </Button>
          ))}
        </div>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : !data ? (
        <LoadingRows rows={10} />
      ) : (
        <div className={loading ? "opacity-60 transition-opacity" : "transition-opacity"}>
          <EmployeeTable
            items={data.items}
            sort={state.sort}
            order={state.order}
            onSort={(column) => navigate(nextSort(state, column))}
          />
          <Pagination
            page={state.page}
            pageSize={state.page_size}
            total={data.total}
            onPage={(page) => navigate({ page })}
            onPageSize={(page_size) => navigate({ page_size })}
          />
        </div>
      )}
    </>
  );
}
