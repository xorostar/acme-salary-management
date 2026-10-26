"use client";

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { ErrorState, LoadingRows, PageHeader } from "@/components/common";
import { AdminOnly } from "@/components/employees/admin-only";
import { EmployeeForm } from "@/components/employees/employee-form";
import { api } from "@/lib/api";
import { useReference } from "@/lib/reference";
import { useApi } from "@/lib/use-api";

const EDITABLE = [
  "employee_number",
  "first_name",
  "last_name",
  "email",
  "country_code",
  "currency_code",
  "department",
  "job_title",
  "level",
  "hire_date",
];

export function EditEmployee() {
  const { id } = useParams();
  const router = useRouter();
  const reference = useReference();
  const { data: employee, error, reload } = useApi(() => api.employee(id), id);

  async function save(values) {
    const { salary_change, ...fields } = values;
    await api.updateEmployee(id, { ...fields, version: employee.version, salary_change });
    toast.success("Changes saved");
    router.push(`/employees/${id}`);
  }

  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!employee || !reference) return <LoadingRows rows={8} />;

  const initial = Object.fromEntries(EDITABLE.map((k) => [k, employee[k] ?? ""]));
  return (
    <AdminOnly>
      <PageHeader
        title={`Edit ${employee.first_name} ${employee.last_name}`}
        description="To change pay, use “Record salary change” on the profile, so history keeps a reason."
      />
      <EmployeeForm
        reference={reference}
        initial={initial}
        original={employee}
        onSubmit={save}
        submitLabel="Save changes"
        onCancel={() => router.back()}
      />
    </AdminOnly>
  );
}
