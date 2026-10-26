"use client";

import { useState } from "react";

import { Field, todayIso } from "@/components/common";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { currencyForCountry } from "@/lib/reference";

export const EMPTY_EMPLOYEE = {
  employee_number: "",
  first_name: "",
  last_name: "",
  email: "",
  country_code: "",
  currency_code: "",
  department: "",
  job_title: "",
  level: "",
  hire_date: "",
  annual_salary: "",
};

/**
 * Create and edit share this form. On edit, changing currency (a relocation)
 * requires a starting salary in the new currency, mirroring the API rule.
 */
export function EmployeeForm({ reference, initial, original, onSubmit, submitLabel, onCancel }) {
  const editing = Boolean(original);
  const [values, setValues] = useState(initial);
  const [change, setChange] = useState({ annual_salary: "", effective_date: todayIso() });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [busy, setBusy] = useState(false);
  const currencyChanged = editing && values.currency_code !== original.currency_code;

  const set = (key) => (e) => {
    const value = e.target.value;
    setValues((v) => {
      const next = { ...v, [key]: value };
      // Default the currency to the country's, which is right for almost everyone.
      if (key === "country_code") next.currency_code = currencyForCountry(reference, value);
      return next;
    });
  };

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    setFormError(null);
    try {
      const body = { ...values };
      if (currencyChanged) {
        body.salary_change = { ...change, reason: "Relocation" };
      }
      await onSubmit(body);
    } catch (err) {
      const fieldErrors = err.byField ?? {};
      setErrors(fieldErrors);
      if (!Object.keys(fieldErrors).length || err.status === 409) setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const text = (key, label, props = {}) => (
    <Field id={key} label={label} error={errors[key]}>
      {(aria) => <Input {...aria} value={values[key]} onChange={set(key)} {...props} />}
    </Field>
  );
  const select = (key, label, options) => (
    <Field id={key} label={label} error={errors[key]}>
      {(aria) => (
        <NativeSelect {...aria} value={values[key]} onChange={set(key)} required>
          <option value="" disabled>
            Choose…
          </option>
          {options.map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </NativeSelect>
      )}
    </Field>
  );

  return (
    <form onSubmit={submit} className="max-w-3xl space-y-6" noValidate>
      {formError && (
        <Alert variant="destructive">
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}
      <fieldset className="grid gap-4 sm:grid-cols-2">
        <legend className="mb-2 text-sm font-medium">Person</legend>
        {text("first_name", "First name", { autoComplete: "off" })}
        {text("last_name", "Last name", { autoComplete: "off" })}
        {text("email", "Work email", { type: "email", autoComplete: "off" })}
        {text("employee_number", "Employee number", { className: "font-mono" })}
      </fieldset>

      <fieldset className="grid gap-4 sm:grid-cols-2">
        <legend className="mb-2 text-sm font-medium">Role</legend>
        {text("job_title", "Job title")}
        {select("department", "Department", (reference?.departments ?? []).map((d) => [d, d]))}
        {select("level", "Level", (reference?.levels ?? []).map((l) => [l, l]))}
        {text("hire_date", "Hire date", { type: "date" })}
      </fieldset>

      <fieldset className="grid gap-4 sm:grid-cols-2">
        <legend className="mb-2 text-sm font-medium">Location and pay</legend>
        {select("country_code", "Country", (reference?.countries ?? []).map((c) => [c.code, c.name]))}
        {select(
          "currency_code",
          "Pay currency",
          (reference?.currencies ?? []).map((c) => [c.code, c.code]),
        )}
        {!editing && (
          <Field
            id="annual_salary"
            label={`Starting annual salary${values.currency_code ? ` (${values.currency_code})` : ""}`}
            error={errors.annual_salary}
            hint="Recorded as the first entry in salary history, effective on the hire date."
          >
            {(aria) => (
              <Input
                {...aria}
                inputMode="decimal"
                placeholder="85000"
                value={values.annual_salary}
                onChange={set("annual_salary")}
              />
            )}
          </Field>
        )}
      </fieldset>

      {currencyChanged && (
        <fieldset className="grid gap-4 rounded-lg border border-dashed p-4 sm:grid-cols-2">
          <legend className="px-1 text-sm font-medium">
            Relocation: salary in {values.currency_code}
          </legend>
          <p className="text-sm text-muted-foreground sm:col-span-2">
            Changing pay currency records a new salary in that currency. History in{" "}
            {original.currency_code} is kept.
          </p>
          <Field id="change_amount" label={`New annual salary (${values.currency_code})`}>
            {(aria) => (
              <Input
                {...aria}
                inputMode="decimal"
                value={change.annual_salary}
                onChange={(e) => setChange((c) => ({ ...c, annual_salary: e.target.value }))}
              />
            )}
          </Field>
          <Field id="change_date" label="Effective from">
            {(aria) => (
              <Input
                {...aria}
                type="date"
                value={change.effective_date}
                onChange={(e) => setChange((c) => ({ ...c, effective_date: e.target.value }))}
              />
            )}
          </Field>
        </fieldset>
      )}

      <div className="flex gap-2">
        <Button type="submit" disabled={busy}>
          {busy ? "Saving…" : submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
