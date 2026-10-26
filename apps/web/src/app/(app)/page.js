import { Suspense } from "react";

import { LoadingRows } from "@/components/common";
import { Dashboard } from "@/components/dashboard/dashboard";

export const metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    <Suspense fallback={<LoadingRows />}>
      <Dashboard />
    </Suspense>
  );
}
