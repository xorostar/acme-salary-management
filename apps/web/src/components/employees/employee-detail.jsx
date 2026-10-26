"use client";

import { ArrowLeftIcon, PencilIcon, TrendingUpIcon, UserMinusIcon, UserPlusIcon } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { ErrorState, formatDate, LoadingRows, todayIso } from "@/components/common";
import { ReactivateDialog, SalaryChangeDialog, TerminateDialog } from "@/components/employees/dialogs";
import { SalaryHistory } from "@/components/employees/salary-history";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatMoney } from "@/lib/money";
import { useApi } from "@/lib/use-api";

export function EmployeeDetail() {
  const { id } = useParams();
  const { isAdmin } = useAuth();
  const { data: e, error, reload } = useApi(() => api.employee(id), id);
  const [dialog, setDialog] = useState(null);

  if (error) {
    return error.status === 404 ? (
      <p className="py-12 text-center text-muted-foreground">This employee does not exist.</p>
    ) : (
      <ErrorState error={error} onRetry={reload} />
    );
  }
  if (!e) return <LoadingRows rows={8} />;

  const today = todayIso();
  const scheduled = e.salary_history.filter((h) => h.effective_date > today);
  const close = (changed) => {
    setDialog(null);
    if (changed) reload();
  };

  return (
    <>
      <Link
        href="/employees"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeftIcon className="size-4" /> Employees
      </Link>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">
              {e.first_name} {e.last_name}
            </h1>
            {e.is_active ? (
              e.termination_date ? (
                <Badge variant="outline">Leaving {formatDate(e.termination_date)}</Badge>
              ) : (
                <Badge variant="secondary">Active</Badge>
              )
            ) : (
              <Badge variant="destructive">Left {formatDate(e.termination_date)}</Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {e.job_title} · {e.level} · {e.department} · {e.country_name}
          </p>
        </div>
        {isAdmin && (
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setDialog("salary")}>
              <TrendingUpIcon /> Record salary change
            </Button>
            <Link href={`/employees/${e.id}/edit`} className={buttonVariants({ variant: "outline" })}>
              <PencilIcon /> Edit details
            </Link>
            {e.termination_date && !e.is_active ? (
              <Button variant="outline" onClick={() => setDialog("reactivate")}>
                <UserPlusIcon /> Reactivate
              </Button>
            ) : (
              <Button variant="outline" onClick={() => setDialog("terminate")}>
                <UserMinusIcon /> {e.termination_date ? "Change leaving date" : "Terminate"}
              </Button>
            )}
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Current annual salary</CardDescription>
            <CardTitle className="text-3xl tabular-nums">
              {e.current_salary
                ? formatMoney(e.current_salary.annual_amount_minor, e.currency_code, { cents: true })
                : "Not set"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {e.current_salary && (
              <p className="text-muted-foreground">
                Since {formatDate(e.current_salary.effective_date)}
              </p>
            )}
            {scheduled.map((s) => (
              <p key={s.id} className="rounded-md bg-muted px-2 py-1.5">
                Scheduled: {formatMoney(s.annual_amount_minor, s.currency_code)} from{" "}
                {formatDate(s.effective_date)} ({s.reason})
              </p>
            ))}
            <dl className="grid grid-cols-2 gap-y-2 border-t pt-3">
              <dt className="text-muted-foreground">Employee no.</dt>
              <dd className="font-mono">{e.employee_number}</dd>
              <dt className="text-muted-foreground">Email</dt>
              <dd className="truncate" title={e.email}>
                {e.email}
              </dd>
              <dt className="text-muted-foreground">Hired</dt>
              <dd>{formatDate(e.hire_date)}</dd>
              <dt className="text-muted-foreground">Pay currency</dt>
              <dd>{e.currency_code}</dd>
            </dl>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Salary history</CardTitle>
            <CardDescription>
              Every change is kept with its date, reason and who recorded it. Nothing is
              overwritten.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SalaryHistory employee={e} today={today} />
          </CardContent>
        </Card>
      </div>

      {dialog === "salary" && <SalaryChangeDialog employee={e} onClose={close} />}
      {dialog === "terminate" && <TerminateDialog employee={e} onClose={close} />}
      {dialog === "reactivate" && <ReactivateDialog employee={e} onClose={close} />}
    </>
  );
}
