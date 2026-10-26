"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { LoadingRows, PageHeader } from "@/components/common";
import { EMPTY_EMPLOYEE, EmployeeForm } from "@/components/employees/employee-form";
import { AdminOnly } from "@/components/employees/admin-only";
import { api } from "@/lib/api";
import { useReference } from "@/lib/reference";

export function NewEmployee() {
  const reference = useReference();
  const router = useRouter();

  async function create(values) {
    const created = await api.createEmployee(values);
    toast.success(`${created.first_name} ${created.last_name} added`);
    router.push(`/employees/${created.id}`);
  }

  return (
    <AdminOnly>
      <PageHeader title="Add employee" description="A new hire, with their starting salary." />
      {reference ? (
        <EmployeeForm
          reference={reference}
          initial={EMPTY_EMPLOYEE}
          onSubmit={create}
          submitLabel="Add employee"
          onCancel={() => router.back()}
        />
      ) : (
        <LoadingRows rows={6} />
      )}
    </AdminOnly>
  );
}
