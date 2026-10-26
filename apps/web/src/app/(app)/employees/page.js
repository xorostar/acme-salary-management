import { Suspense } from "react";

import { LoadingRows } from "@/components/common";
import { Directory } from "@/components/employees/directory";

export const metadata = { title: "Employees" };

export default function EmployeesPage() {
  return (
    <Suspense fallback={<LoadingRows />}>
      <Directory />
    </Suspense>
  );
}
