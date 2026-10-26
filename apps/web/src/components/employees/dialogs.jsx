"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Field, formatDate, todayIso } from "@/components/common";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { api } from "@/lib/api";
import { exponentFor, formatMoney, formatPercent, percentChange } from "@/lib/money";
import { useReference } from "@/lib/reference";

/** Shared dialog chrome: submit handling, busy state and API error display. */
function ActionDialog({ title, description, onClose, onSubmit, submitLabel, children, destructive }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit();
      onClose(true);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose(false)}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={submit} className="grid gap-4" noValidate>
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            {description && <DialogDescription>{description}</DialogDescription>}
          </DialogHeader>
          {typeof children === "function" ? children(error?.byField ?? {}) : children}
          {error && (!error.fieldErrors.length || error.status === 409) && (
            <Alert variant="destructive">
              <AlertDescription>{error.message}</AlertDescription>
            </Alert>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onClose(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy} variant={destructive ? "destructive" : "default"}>
              {busy ? "Saving…" : submitLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function SalaryChangeDialog({ employee, onClose }) {
  const reference = useReference();
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(todayIso());
  const [reason, setReason] = useState("Annual review");
  const [other, setOther] = useState("");
  const currency = employee.currency_code;
  const current = employee.current_salary?.annual_amount_minor;
  const parsed = Number(amount);
  const preview =
    amount && Number.isFinite(parsed) && current
      ? percentChange(current, Math.round(parsed * 10 ** exponentFor(currency)))
      : null;

  return (
    <ActionDialog
      title="Record salary change"
      description={`${employee.first_name} ${employee.last_name} is paid ${current ? formatMoney(current, currency) : "nothing yet"} today.`}
      submitLabel="Record change"
      onClose={onClose}
      onSubmit={async () => {
        await api.addSalaryEvent(employee.id, {
          annual_salary: amount,
          effective_date: date,
          reason: reason === "Other" ? other || "Other" : reason,
        });
        toast.success(
          date > todayIso()
            ? `Change scheduled for ${formatDate(date)}`
            : "Salary change recorded",
        );
      }}
    >
      {(errors) => (
        <>
          <Field
            id="amount"
            label={`New annual salary (${currency})`}
            error={errors.annual_salary || errors.annual_amount_minor}
            hint={preview !== null ? `${formatPercent(preview)} vs today` : undefined}
          >
            {(aria) => (
              <Input
                {...aria}
                autoFocus
                inputMode="decimal"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder={current ? String(current / 10 ** exponentFor(currency)) : ""}
              />
            )}
          </Field>
          <Field
            id="effective"
            label="Effective from"
            error={errors.effective_date}
            hint="A future date schedules the change; today's figures are unaffected until then."
          >
            {(aria) => (
              <Input {...aria} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            )}
          </Field>
          <Field id="reason" label="Reason" error={errors.reason}>
            {(aria) => (
              <NativeSelect {...aria} value={reason} onChange={(e) => setReason(e.target.value)}>
                {(reference?.salary_change_reasons ?? [])
                  .filter((r) => r !== "Hire")
                  .map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
              </NativeSelect>
            )}
          </Field>
          {reason === "Other" && (
            <Field id="other" label="Describe the reason">
              {(aria) => (
                <Input {...aria} value={other} onChange={(e) => setOther(e.target.value)} />
              )}
            </Field>
          )}
        </>
      )}
    </ActionDialog>
  );
}

export function TerminateDialog({ employee, onClose }) {
  const [date, setDate] = useState(employee.termination_date ?? todayIso());
  return (
    <ActionDialog
      title={`Terminate ${employee.first_name} ${employee.last_name}`}
      description="They leave headcount and payroll after this date. Their record and salary history are kept."
      submitLabel="Terminate"
      destructive
      onClose={onClose}
      onSubmit={async () => {
        await api.terminate(employee.id, { termination_date: date, version: employee.version });
        toast.success("Termination recorded");
      }}
    >
      {(errors) => (
        <Field id="termination" label="Last day of employment" error={errors.termination_date}>
          {(aria) => (
            <Input {...aria} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          )}
        </Field>
      )}
    </ActionDialog>
  );
}

export function ReactivateDialog({ employee, onClose }) {
  return (
    <ActionDialog
      title={`Reactivate ${employee.first_name} ${employee.last_name}`}
      description="Clears the termination date. Their previous salary history applies again."
      submitLabel="Reactivate"
      onClose={onClose}
      onSubmit={async () => {
        await api.reactivate(employee.id, { version: employee.version });
        toast.success("Employee reactivated");
      }}
    />
  );
}
