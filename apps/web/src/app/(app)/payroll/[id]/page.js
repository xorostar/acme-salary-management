import { Suspense } from "react";

import { LoadingRows } from "@/components/common";
import { PayrollRunDetail } from "@/components/payroll/payroll-run-detail";

export const metadata = { title: "Payroll run" };

export default function PayrollRunPage() {
  return (
    <Suspense fallback={<LoadingRows />}>
      <PayrollRunDetail />
    </Suspense>
  );
}
