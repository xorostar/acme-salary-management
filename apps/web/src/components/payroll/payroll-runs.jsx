"use client";

import { PlayIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingRows, PageHeader } from "@/components/common";
import { periodLabel, selectablePeriods } from "@/components/payroll/period";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { useAuth } from "@/lib/auth";
import { formatMoney } from "@/lib/money";
import { useApi } from "@/lib/use-api";

export function PayrollRuns() {
  const { isAdmin } = useAuth();
  const router = useRouter();
  const { data: runs, error, reload } = useApi(() => api.payrollRuns(), "runs");
  const [periods] = useState(() => selectablePeriods());
  // periods[0] is next month (allowed for preparing ahead); default to this month.
  const [choice, setChoice] = useState(1);
  const [busy, setBusy] = useState(false);

  const existing = new Set((runs ?? []).map((r) => `${r.period_year}-${r.period_month}`));
  const selected = periods[choice];
  const alreadyRun = existing.has(`${selected.year}-${selected.month}`);

  async function create() {
    setBusy(true);
    try {
      const run = await api.createPayrollRun(selected.year, selected.month);
      toast.success(`Payroll for ${selected.label} created`);
      router.push(`/payroll/${run.id}`);
    } catch (err) {
      toast.error(err.fieldErrors?.[0]?.message ?? err.message);
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Payroll runs"
        description="A run freezes what each employee is owed for a month. It records amounts; it does not pay anyone."
      />

      {isAdmin && (
        <Card className="mb-6 max-w-2xl">
          <CardHeader>
            <CardTitle>Run payroll</CardTitle>
            <CardDescription>
              Includes everyone employed on the last day of the month, at the salary in force that
              day ÷ 12. Later salary changes never alter a finished run.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-2">
            <NativeSelect
              aria-label="Payroll period"
              value={choice}
              onChange={(e) => setChoice(Number(e.target.value))}
              className="w-48"
            >
              {periods.map((p, i) => (
                <option key={p.label} value={i}>
                  {p.label}
                  {existing.has(`${p.year}-${p.month}`) ? " (done)" : ""}
                </option>
              ))}
            </NativeSelect>
            <Button onClick={create} disabled={busy || alreadyRun}>
              <PlayIcon /> {busy ? "Running…" : `Run ${selected.label}`}
            </Button>
            {alreadyRun && (
              <span className="text-sm text-muted-foreground">Already run for this month.</span>
            )}
          </CardContent>
        </Card>
      )}

      {error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : !runs ? (
        <LoadingRows rows={4} />
      ) : runs.length === 0 ? (
        <EmptyState title="No payroll runs yet">
          {isAdmin ? "Choose a month above to create the first one." : "An HR admin can create one."}
        </EmptyState>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Period</TableHead>
              <TableHead className="text-right">Employees</TableHead>
              <TableHead className="text-right">Total (USD)</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((r) => (
              <TableRow key={r.id}>
                <TableCell>
                  <Link href={`/payroll/${r.id}`} className="font-medium hover:underline">
                    {periodLabel(r.period_year, r.period_month)}
                  </Link>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {r.employee_count.toLocaleString("en-US")}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(r.total_usd_minor, "USD")}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {new Date(r.created_at + "Z").toLocaleString("en-GB")}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </>
  );
}
