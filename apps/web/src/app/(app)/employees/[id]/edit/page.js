import { Suspense } from "react";

import { LoadingRows } from "@/components/common";
import { EditEmployee } from "@/components/employees/edit-employee";

export const metadata = { title: "Edit employee" };

export default function EditEmployeePage() {
  return (
    <Suspense fallback={<LoadingRows />}>
      <EditEmployee />
    </Suspense>
  );
}
