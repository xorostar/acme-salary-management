import { Suspense } from "react";

import { LoadingRows } from "@/components/common";
import { EmployeeDetail } from "@/components/employees/employee-detail";

export const metadata = { title: "Employee" };

export default function EmployeePage() {
  return (
    <Suspense fallback={<LoadingRows />}>
      <EmployeeDetail />
    </Suspense>
  );
}
