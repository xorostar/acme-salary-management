"use client";

import { ArrowLeftIcon, DownloadIcon } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ErrorState, LoadingRows, PageHeader, StatCard } from "@/components/common";
import { Pagination } from "@/components/employees/pagination";
import { periodLabel } from "@/components/payroll/period";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/money";
import { useApi } from "@/lib/use-api";

const PAGE_SIZE = 50;

export function PayrollRunDetail() {
  const { id } = useParams();
  const run = useApi(() => api.payrollRun(id), id);
  const [country, setCountry] = useState("");
  const [page, setPage] = useState(1);
  const lines = useApi(
    () => api.payrollLines(id, { country_code: country, page, page_size: PAGE_SIZE }),
    `${id}|${country}|${page}`,
  );

  if (run.error) return <ErrorState error={run.error} onRetry={run.reload} />;
  if (!run.data) return <LoadingRows rows={8} />;
  const r = run.data;

  async function exportCsv() {
    try {
      await api.exportPayrollRun(id);
    } catch (e) {
      toast.error(`Export failed: ${e.message}`);
    }
  }

  return (
    <>
      <Link
        href="/payroll"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeftIcon className="size-4" /> Payroll runs
      </Link>
      <PageHeader
        title={`Payroll · ${periodLabel(r.period_year, r.period_month)}`}
        description="Frozen when created. Amounts are monthly, in each employee's pay currency."
        actions={
          <Button variant="outline" onClick={exportCsv}>
            <DownloadIcon /> Export CSV
          </Button>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Employees paid" value={r.employee_count.toLocaleString("en-US")} />
        <StatCard label="Total (USD)" value={formatMoney(r.total_usd_minor, "USD")} />
        <StatCard label="Countries" value={r.countries.length} />
        <StatCard
          label="Created"
          value={new Date(r.created_at + "Z").toLocaleDateString("en-GB")}
        />
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>By country</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Country</TableHead>
                <TableHead className="text-right">Employees</TableHead>
                <TableHead className="text-right">Local total</TableHead>
                <TableHead className="text-right">USD total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {r.countries.map((c) => (
                <TableRow key={c.country_code}>
                  <TableCell className="font-medium">{c.country_name}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {c.employee_count.toLocaleString("en-US")}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(c.amount_minor, c.currency_code)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(c.amount_usd_minor, "USD")}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle>Lines</CardTitle>
          <NativeSelect
            aria-label="Filter lines by country"
            value={country}
            onChange={(e) => {
              setCountry(e.target.value);
              setPage(1);
            }}
            className="w-44"
          >
            <option value="">All countries</option>
            {r.countries.map((c) => (
              <option key={c.country_code} value={c.country_code}>
                {c.country_name}
              </option>
            ))}
          </NativeSelect>
        </CardHeader>
        <CardContent>
          {lines.error ? (
            <ErrorState error={lines.error} onRetry={lines.reload} />
          ) : !lines.data ? (
            <LoadingRows rows={10} />
          ) : (
            <div className={lines.loading ? "opacity-60" : undefined}>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Employee</TableHead>
                    <TableHead>Department</TableHead>
                    <TableHead className="text-right">Annual</TableHead>
                    <TableHead className="text-right">Monthly</TableHead>
                    <TableHead className="text-right">Rate</TableHead>
                    <TableHead className="text-right">Monthly (USD)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lines.data.items.map((ln) => (
                    <TableRow key={ln.employee_id}>
                      <TableCell>
                        <Link href={`/employees/${ln.employee_id}`} className="hover:underline">
                          {ln.employee_name}
                        </Link>
                        <span className="ml-2 font-mono text-xs text-muted-foreground">
                          {ln.employee_number}
                        </span>
                      </TableCell>
                      <TableCell>{ln.department}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatMoney(ln.annual_amount_minor, ln.currency_code)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatMoney(ln.amount_minor, ln.currency_code, { cents: true })}
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground tabular-nums">
                        {ln.rate_to_usd}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatMoney(ln.amount_usd_minor, "USD", { cents: true })}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={lines.data.total}
                onPage={setPage}
              />
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
